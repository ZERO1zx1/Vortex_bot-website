from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import src.cogs.moderation as moderation_module
from src.cogs.moderation import Moderation
from src.utils import constants


def bare_cog(bot):
    cog = Moderation.__new__(Moderation)
    cog.bot = bot
    cog.voice_times = {}
    cog._processed_weeks = set()
    return cog


def voice_state(channel, *, self_mute=False, deaf=False):
    return SimpleNamespace(channel=channel, self_mute=self_mute, deaf=deaf)


@pytest.mark.asyncio
async def test_voice_sessions_are_scoped_by_guild_and_use_monotonic_time(monkeypatch):
    class DB:
        async def fetch_safe(self, table, filters, single=False):
            return {"user_id": filters["user_id"]}

    cog = bare_cog(SimpleNamespace(db_manager=DB()))
    cog.increment_staff_activity = AsyncMock()
    times = iter((100.0, 110.0, 160.0, 180.0))
    monkeypatch.setattr(
        moderation_module,
        "time",
        SimpleNamespace(monotonic=lambda: next(times)),
    )
    channel = SimpleNamespace(id=1)
    empty = voice_state(None)
    connected = voice_state(channel)
    member_guild_1 = SimpleNamespace(id=42, bot=False, guild=SimpleNamespace(id=5))
    member_guild_2 = SimpleNamespace(id=42, bot=False, guild=SimpleNamespace(id=6))

    await cog.on_voice_state_update(member_guild_1, empty, connected)
    await cog.on_voice_state_update(member_guild_2, empty, connected)
    await cog.on_voice_state_update(member_guild_1, connected, empty)
    await cog.on_voice_state_update(member_guild_2, connected, empty)

    assert cog.voice_times == {}
    assert [call.args for call in cog.increment_staff_activity.await_args_list] == [
        (42, 5, "voice_seconds", 60),
        (42, 6, "voice_seconds", 70),
    ]


@pytest.mark.asyncio
async def test_weekly_winner_is_idempotent_for_existing_guild_week():
    class DB:
        def __init__(self):
            self.inserts = []

        async def fetch_safe(self, table, filters, single=False):
            if table == "staff_weekly_winners":
                return {"id": 1}
            raise AssertionError(f"unexpected read after idempotency guard: {table}")

        async def insert(self, table, data):
            self.inserts.append((table, data))

    db = DB()
    cog = bare_cog(SimpleNamespace(db_manager=db))

    await cog.process_weekly_winner(SimpleNamespace(id=5), week_start=moderation_module.datetime.date(2026, 9, 28))

    assert db.inserts == []


def test_moderation_uses_shared_color_constants():
    assert moderation_module.EMBED_COLOR == constants.EMBED_COLOR
    assert moderation_module.SUCCESS_COLOR == constants.SUCCESS_COLOR
    assert moderation_module.ERROR_COLOR == constants.ERROR_COLOR
