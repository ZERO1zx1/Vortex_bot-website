from __future__ import annotations

import random
from datetime import timedelta

import pytest

from core.database import Database
from core.exceptions import (
    ActionCooldownError,
    CrimeNotFoundError,
    InsufficientFundsError,
    JailedError,
    NotJailedError,
    TargetProtectedError,
    ValidationError,
)
from repositories.log_repo import LogRepository
from repositories.skill_repo import SkillRepository
from repositories.user_repo import UserRepository
from services.economy.crime_service import CrimeService
from services.economy.jail_service import JailService
from services.rpg.skill_service import SkillService
from utils.time_utils import to_db, utcnow


class _Rng(random.Random):
    """Детерминик тестийн RNG — service-ийн `random.Random`-ыг орлоно."""

    def __init__(
        self,
        *,
        roll: float = 0.0,
        integer: int = 100,
        uniform: float = 0.20,
    ) -> None:
        super().__init__()
        self.roll = roll
        self.integer = integer
        self.uniform_value = uniform

    def random(self) -> float:
        return self.roll

    def randint(self, low: int, high: int) -> int:
        return max(low, min(high, self.integer))

    def uniform(self, low: float, high: float) -> float:
        return max(low, min(high, self.uniform_value))


# ── Jail ─────────────────────────────────────────────────────────────────
async def test_imprison_bail_and_release(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    jail = JailService(db, users=users)

    result = await jail.imprison(1, minutes=10, bail_cost=800, reason="test")
    assert result.minutes == 10
    assert result.bail_cost == 800
    status = await jail.status(1)
    assert status.jailed is True
    assert status.remaining_sec > 9 * 60
    with pytest.raises(JailedError):
        await jail.ensure_not_jailed(1)

    with pytest.raises(InsufficientFundsError, match="Батлан даалт"):
        await jail.bail(1)

    await users.credit_wallet(1, 1_000)
    released = await jail.bail(1)
    assert released.reason == "bail"
    assert (await users.get(1)).wallet == 700  # type: ignore[union-attr]
    assert (await jail.status(1)).jailed is False
    history = await LogRepository(db).recent_transactions(1)
    assert history[0].source == "bail"
    assert history[0].amount == -800
    with pytest.raises(NotJailedError):
        await jail.bail(1)


async def test_expired_jail_is_released(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.set_jail(1, until=to_db(utcnow() - timedelta(minutes=1)), bail_cost=100)
    jail = JailService(db, users=users)

    assert (await jail.status(1)).jailed is False
    assert await jail.release_if_expired(1) is True
    assert (await users.get(1)).jail_until is None  # type: ignore[union-attr]
    assert await jail.release_if_expired(1) is False


async def test_shadow_step_reduces_jail_time_and_bail(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    skills_repo = SkillRepository(db)
    for _ in range(5):
        await skills_repo.increment_level(1, "shadow_step", 5)
    service = SkillService(db, user_repo=users)
    jail = JailService(db, users=users, skills=service)

    result = await jail.imprison(1, minutes=10, bail_cost=800)
    assert result.minutes == 8  # ceil(10 * 0.75)
    assert result.bail_cost == 600  # floor(800 * 0.75)
    assert (await users.get(1)).jail_bail_cost == 600  # type: ignore[union-attr]


# ── Crime ────────────────────────────────────────────────────────────────
async def test_successful_crime_rewards_and_cooldown(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    service = CrimeService(db, users=users, rng=_Rng(roll=0.0, integer=150))

    result = await service.crime(1, "pickpocket")
    assert result.success is True
    assert result.reward == 150
    assert result.fine == 0
    assert result.xp == 17
    assert result.jailed is False
    assert (await users.get(1)).wallet == 650  # type: ignore[union-attr]
    history = await LogRepository(db).recent_transactions(1)
    assert history[0].source == "crime"

    with pytest.raises(ActionCooldownError):
        await service.crime(1, "pickpocket")


async def test_failed_crime_fines_and_jails(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    service = CrimeService(db, users=users, rng=_Rng(roll=0.99, integer=100))

    result = await service.crime(1, "pickpocket")
    assert result.success is False
    assert result.fine == 100
    assert result.jailed is True
    assert result.jail_until is not None
    user = await users.get(1)
    assert user and user.wallet == 400  # type: ignore[union-attr]
    assert user and user.jail_until is not None  # type: ignore[union-attr]
    with pytest.raises(JailedError):
        await service.crime(1, "pickpocket")


async def test_crime_level_gate(db: Database) -> None:
    service = CrimeService(db, rng=_Rng())
    with pytest.raises(CrimeNotFoundError):
        await service.crime(1, "cyber_hack")
    assert [crime.crime_id for crime in service.crimes_for(1)] == ["pickpocket"]


async def test_rob_success_transfers_wallet(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.get_or_create(2)
    await users.credit_wallet(2, 500)
    service = CrimeService(db, users=users, rng=_Rng(roll=0.0, uniform=0.20))

    result = await service.rob(1, 2)
    assert result.success is True
    assert result.stolen == 200
    assert result.actor_wallet == 700
    assert result.target_wallet == 800
    assert result.jailed is False
    history = await LogRepository(db).recent_transactions(2)
    assert history[0].source == "robbed"
    assert history[0].amount == -200


async def test_failed_rob_fines_and_jails_actor(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.get_or_create(2)
    await users.credit_wallet(2, 500)
    service = CrimeService(db, users=users, rng=_Rng(roll=0.99, uniform=0.20))

    result = await service.rob(1, 2)
    assert result.success is False
    assert result.fine == 75
    assert result.actor_wallet == 425
    assert result.target_wallet == 1_000
    assert result.jailed is True


async def test_rob_guards_self_shield_and_jail(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.get_or_create(2)
    service = CrimeService(db, users=users, rng=_Rng())

    with pytest.raises(ValidationError):
        await service.rob(1, 1)

    await users.set_shield_until(2, to_db(utcnow() + timedelta(hours=1)))
    with pytest.raises(TargetProtectedError):
        await service.rob(1, 2)

    await users.set_shield_until(2, None)
    await users.set_jail(1, until=to_db(utcnow() + timedelta(minutes=5)), bail_cost=100)
    with pytest.raises(JailedError):
        await service.rob(1, 2)


async def test_rob_empty_target_rejected(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.get_or_create(2)
    await users.spend_wallet(2, 500)
    service = CrimeService(db, users=users, rng=_Rng())
    with pytest.raises(ValidationError, match="Wallet"):
        await service.rob(1, 2)
