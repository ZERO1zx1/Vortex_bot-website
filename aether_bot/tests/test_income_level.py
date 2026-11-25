from __future__ import annotations

import random

import pytest

from core.database import Database
from core.event_bus import EventBus
from core.exceptions import ActionCooldownError, JobNotFoundError
from repositories.log_repo import LogRepository
from repositories.user_repo import UserRepository
from services.economy.income_service import IncomeService
from services.rpg.level_service import LevelService
from services.rpg.skill_service import SkillService
from utils.time_utils import to_db, utcnow


def _wire(db: Database) -> tuple[EventBus, LevelService, IncomeService]:
    bus = EventBus()
    users = UserRepository(db)
    skills = SkillService(db, user_repo=users)
    logs = LogRepository(db)
    level = LevelService(db, users=users, logs=logs, event_bus=bus)
    level.subscribe(bus)
    income = IncomeService(
        db,
        users=users,
        logs=logs,
        skills=skills,
        level_service=level,
        event_bus=bus,
        rng=random.Random(7),
    )
    return bus, level, income


async def test_daily_reward_streak_and_cooldown(db: Database) -> None:
    _, _, income = _wire(db)
    result = await income.daily(1)
    assert db.advisory_locks == [1]  # type: ignore[attr-defined]
    assert result.streak == 1
    assert result.reward >= 250
    assert result.xp == 40
    user = await UserRepository(db).get(1)
    assert user and user.wallet == 500 + result.reward  # type: ignore[union-attr]
    assert user and user.xp == 40  # type: ignore[union-attr]

    with pytest.raises(ActionCooldownError):
        await income.daily(1)


async def test_daily_streak_increases_after_a_day(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.set_daily(1, 1, to_db(utcnow().replace(microsecond=0)))
    await db.execute(
        "UPDATE users SET last_daily_at = datetime('now', '-25 hours') WHERE user_id = 1"
    )
    _, _, income = _wire(db)
    result = await income.daily(1)
    assert result.streak == 2


async def test_work_cooldown_and_level_requirement(db: Database) -> None:
    _, _, income = _wire(db)
    result = await income.work(1, "courier")
    assert result.reward >= 80
    assert result.xp == 12
    assert result.cooldown_sec == 1800
    with pytest.raises(ActionCooldownError):
        await income.work(1, "courier")
    with pytest.raises(JobNotFoundError):
        await income.work(1, "aether_engineer")


async def test_level_up_awards_sp_and_coins(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    level = LevelService(db, users=users)
    result = await level.award_xp(1, 100)
    assert result.previous_level == 1
    assert result.new_level == 2
    assert result.xp_remaining == 0
    assert result.skill_points_awarded == 2
    assert result.coins_awarded == 400
    user = await users.get(1)
    assert user and user.level == 2  # type: ignore[union-attr]
    assert user and user.skill_points == 2  # type: ignore[union-attr]
    assert user and user.wallet == 900  # type: ignore[union-attr]


async def test_level_progress(db: Database) -> None:
    level = LevelService(db)
    await UserRepository(db).get_or_create(1)
    progress = await level.progress(1)
    assert progress.required_xp == 100
    assert progress.percent == 0.0
