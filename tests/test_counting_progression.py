from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.cogs.games.counting import (
    MILESTONE_XP,
    Counting,
    CountingReward,
    calculate_counting_reward,
    counting_level,
    counting_penalty,
    counting_xp_base,
    has_weekly_shield,
    next_counting_level_xp,
)


class FakeDB:
    def __init__(self):
        self.rows = {}

    async def fetch_one(self, table, filters):
        row = self.rows.get((str(filters["guild_id"]), str(filters["user_id"])))
        return dict(row) if row else None

    async def upsert(self, table, data, on_conflict=None):
        self.rows[(str(data["guild_id"]), str(data["user_id"]))] = dict(data)
        return [dict(data)]


class FakeCountingDB:
    def __init__(self):
        self.tables = {
            "counting_config": [
                {
                    "guild_id": "5",
                    "channel_id": 10,
                    "enabled": True,
                    "delete_messages": False,
                    "math_mode": True,
                    "failed_role_id": None,
                    "reliable_role_id": None,
                    "save_role_id": None,
                    "level_5_role_id": None,
                    "level_20_role_id": None,
                    "level_50_role_id": None,
                    "high_score": 0,
                    "best_streak": 0,
                }
            ],
            "counting_progress": [],
            "counting_stats": [],
        }

    @staticmethod
    def _matches(row, filters):
        return all(str(row.get(key)) == str(value) for key, value in filters.items())

    async def fetch_one(self, table, filters):
        return next(
            (dict(row) for row in self.tables[table] if self._matches(row, filters)),
            None,
        )

    async def fetch_safe(self, table, filters, single=False):
        return await self.fetch_one(table, filters)

    async def upsert(self, table, data, on_conflict=None):
        keys = (on_conflict or "guild_id,user_id").split(",")
        filters = {key: data.get(key) for key in keys}
        for row in self.tables[table]:
            if self._matches(row, filters):
                row.update(dict(data))
                return [dict(row)]
        self.tables[table].append(dict(data))
        return [dict(data)]

    async def update(self, table, filters, data):
        for row in self.tables[table]:
            if self._matches(row, filters):
                row.update(dict(data))
                return [dict(row)]
        return []

    async def insert(self, table, data):
        self.tables[table].append(dict(data))
        return [dict(data)]


def make_message(number: str, user_id: int, channel, guild):
    author = SimpleNamespace(
        id=user_id,
        bot=False,
        mention=f"<@{user_id}>",
        roles=[],
        guild=guild,
        add_roles=AsyncMock(),
    )
    return SimpleNamespace(
        content=number,
        author=author,
        guild=guild,
        channel=channel,
        add_reaction=AsyncMock(),
        delete=AsyncMock(),
    )


def test_dynamic_xp_bands_are_bounded_and_monotonic():
    assert counting_xp_base(1) == 5
    assert counting_xp_base(100) == 6
    assert counting_xp_base(500) == 8
    assert counting_xp_base(1_000) == 10
    assert counting_xp_base(5_000) == 12
    assert counting_xp_base(1_000_000) == 12


def test_milestone_and_expression_bonuses_stack():
    reward = calculate_counting_reward(
        500,
        used_expression=True,
        recent_users=[1, 2, 3],
        xp_on_cooldown=False,
    )

    assert reward.base == 8
    assert reward.math_bonus == 3
    assert reward.milestone_bonus == MILESTONE_XP[500]
    assert reward.total == 61


def test_xp_cooldown_suppresses_repeatable_reward_but_not_jackpot():
    ordinary = calculate_counting_reward(
        501,
        used_expression=True,
        recent_users=[1, 2, 3],
        xp_on_cooldown=True,
    )
    milestone = calculate_counting_reward(
        777,
        used_expression=False,
        recent_users=[1, 2],
        xp_on_cooldown=True,
    )

    assert ordinary.total == 0
    assert milestone.total == MILESTONE_XP[777]


def test_two_person_farm_has_diminishing_returns_until_a_third_joins():
    early = calculate_counting_reward(
        50,
        used_expression=False,
        recent_users=[1, 2] * 4,
        xp_on_cooldown=False,
    )
    sustained = calculate_counting_reward(
        50,
        used_expression=False,
        recent_users=[1, 2] * 7,
        xp_on_cooldown=False,
    )
    farmed = calculate_counting_reward(
        50,
        used_expression=False,
        recent_users=[1, 2] * 10,
        xp_on_cooldown=False,
    )
    social = calculate_counting_reward(
        50,
        used_expression=False,
        recent_users=[1, 2] * 9 + [3],
        xp_on_cooldown=False,
    )

    assert early.base == 5
    assert sustained.base == 2
    assert farmed.base == 1
    assert social.base == 5


def test_penalty_scales_slowly_and_is_capped():
    assert counting_penalty(10) == 5
    assert counting_penalty(500) == 10
    assert counting_penalty(1_000) == 15
    assert counting_penalty(5_000) == 55
    assert counting_penalty(1_000_000) == 100


def test_levels_use_cumulative_quadratic_thresholds():
    assert counting_level(0) == 0
    assert counting_level(99) == 0
    assert counting_level(100) == 1
    assert counting_level(399) == 1
    assert counting_level(400) == 2
    assert next_counting_level_xp(2) == 900


def test_level_30_shield_refreshes_once_per_week():
    now = 2_000_000
    assert not has_weekly_shield(level=29, last_used_at=None, now=now)
    assert has_weekly_shield(level=30, last_used_at=None, now=now)
    assert not has_weekly_shield(level=30, last_used_at=now - 60, now=now)
    assert has_weekly_shield(level=30, last_used_at=now - 604_800, now=now)


@pytest.mark.asyncio
async def test_correct_reward_updates_spendable_and_lifetime_xp():
    db = FakeDB()
    cog = Counting(SimpleNamespace(db_manager=db))

    stats, gained = await cog.record_correct_count(
        5,
        7,
        streak=20,
        reward=CountingReward(8, 3, 100, 100),
        now=1_000,
    )

    assert stats["xp_balance"] == 111
    assert stats["lifetime_xp"] == 111
    assert stats["level"] == 1
    assert stats["correct"] == 1
    assert stats["best_streak"] == 20
    assert gained == 1


@pytest.mark.asyncio
async def test_failure_uses_shield_then_save_then_capped_penalty():
    db = FakeDB()
    db.rows[("5", "7")] = {
        "guild_id": "5",
        "user_id": "7",
        "xp_balance": 1_000,
        "lifetime_xp": 90_000,
        "level": 30,
        "save_tokens": 1,
    }
    cog = Counting(SimpleNamespace(db_manager=db))

    protection, penalty, _ = await cog.record_failed_count(
        5, 7, current_count=5_000, now=1_000_000
    )
    assert (protection, penalty) == ("shield", 0)

    protection, penalty, stats = await cog.record_failed_count(
        5, 7, current_count=5_000, now=1_000_100
    )
    assert (protection, penalty) == ("save", 0)
    assert stats["save_tokens"] == 0

    protection, penalty, stats = await cog.record_failed_count(
        5, 7, current_count=1_000_000, now=1_000_200
    )
    assert (protection, penalty) == (None, 100)
    assert stats["xp_balance"] == 900


@pytest.mark.asyncio
async def test_message_flow_advances_server_streak_and_resets_with_penalty(monkeypatch):
    db = FakeCountingDB()
    bot = SimpleNamespace(db_manager=db, get_cog=lambda name: None)
    cog = Counting(bot)
    channel = SimpleNamespace(id=10, send=AsyncMock())
    guild = SimpleNamespace(id=5, get_role=lambda role_id: None)
    ticks = iter([1_000, 1_001, 1_010])
    monkeypatch.setattr("src.cogs.games.counting.time.time", lambda: next(ticks))

    first = make_message("1", 1, channel, guild)
    second = make_message("2", 2, channel, guild)
    wrong = make_message("9", 1, channel, guild)
    await cog.on_message(first)
    await cog.on_message(second)

    progress = db.tables["counting_progress"][0]
    assert progress["current_count"] == 2
    assert progress["streak"] == 2
    first_stats = next(row for row in db.tables["counting_stats"] if row["user_id"] == "1")
    assert first_stats["xp_balance"] == 5

    await cog.on_message(wrong)

    assert progress["current_count"] == 0
    first_stats = next(row for row in db.tables["counting_stats"] if row["user_id"] == "1")
    assert first_stats["xp_balance"] == 0
    assert first_stats["wrong"] == 1
    channel.send.assert_awaited()


def test_counting_progression_migration_is_in_incremental_and_bootstrap_sql():
    incremental = Path("src/database/migrations/010_counting_progression.sql").read_text()
    bootstrap = Path("src/database/migrations/000_aether_complete.sql").read_text()

    for sql in (incremental, bootstrap):
        assert "xp_balance BIGINT NOT NULL DEFAULT 0" in sql
        assert "lifetime_xp BIGINT NOT NULL DEFAULT 0" in sql
        assert "save_tokens INT NOT NULL DEFAULT 0" in sql
        assert "recent_users JSONB NOT NULL" in sql
        assert "level_50_role_id BIGINT" in sql
