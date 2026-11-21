from __future__ import annotations

import random
from datetime import timedelta
from typing import Any

import pytest

from core.database import Database
from core.exceptions import (
    ActionCooldownError,
    BossNotFoundError,
    DungeonNotFoundError,
    GameStateError,
    InsufficientFundsError,
    InvalidBetError,
    SkillNotUsableError,
    ValidationError,
)
from repositories.log_repo import LogRepository
from repositories.skill_repo import SkillRepository
from repositories.user_repo import UserRepository
from services.games.adventure_service import AdventureService, load_dungeons
from services.games.boss_service import BossService
from services.games.duel_service import DuelService
from services.games.hunt_fish_service import (
    FISH_TABLE,
    HUNT_TABLE,
    HuntFishService,
)
from utils.time_utils import to_db, utcnow


class StubRng(random.Random):
    def __init__(
        self,
        *,
        random_value: float = 0.9,
        int_value: int = 10,
        choice_value: Any = None,
        choices_values: list[Any] | None = None,
    ) -> None:
        super().__init__()
        self.random_value = random_value
        self.int_value = int_value
        self.choice_value = choice_value
        self.choices_values = choices_values

    def random(self) -> float:
        return self.random_value

    def randint(self, low: int, high: int) -> int:
        return self.int_value

    def choice(self, seq: Any) -> Any:
        return self.choice_value if self.choice_value is not None else seq[0]

    def choices(  # type: ignore[override]
        self, population: Any, **kwargs: Any
    ) -> list[Any]:
        if self.choices_values is not None:
            return list(self.choices_values)
        return [population[0]]


# ── Adventure ────────────────────────────────────────────────────────────
async def test_adventure_success_and_failure(db: Database) -> None:
    service = AdventureService(db, rng=StubRng(random_value=0.9, int_value=200))
    result = await service.explore(1, "neon_cavern")
    assert result.success is True
    assert result.reward == 200
    assert result.xp == 25
    assert result.wallet == 700
    assert result.dungeon.dungeon_id == "neon_cavern"
    with pytest.raises(ActionCooldownError):
        await service.explore(1, "neon_cavern")

    failing = AdventureService(db, rng=StubRng(random_value=0.0, int_value=200))
    result = await failing.explore(2, "neon_cavern")
    assert result.success is False
    assert result.reward == 0
    assert result.xp == 5
    assert result.wallet == 500


async def test_adventure_level_gate_and_catalog(db: Database) -> None:
    assert len(load_dungeons()) == 4
    service = AdventureService(db)
    with pytest.raises(DungeonNotFoundError):
        await service.explore(1, "astral_gate")
    with pytest.raises(DungeonNotFoundError):
        await service.explore(1, "unknown")
    assert [d.dungeon_id for d in service.dungeons_for(1)] == ["neon_cavern"]


# ── Hunt / Fish ──────────────────────────────────────────────────────────
async def test_hunt_and_fish_rewards_and_cooldowns(db: Database) -> None:
    service = HuntFishService(
        db,
        rng=StubRng(int_value=75, choices_values=[HUNT_TABLE[0]]),
    )
    result = await service.hunt(1)
    assert result.kind == "hunt"
    assert result.catch == "Neon Rabbit"
    assert result.reward == 75
    assert result.xp == 10
    assert result.wallet == 575
    with pytest.raises(ActionCooldownError):
        await service.hunt(1)

    fish_service = HuntFishService(
        db,
        rng=StubRng(int_value=55, choices_values=[FISH_TABLE[0]]),
    )
    result = await fish_service.fish(1)
    assert result.kind == "fish"
    assert result.catch == "Rust Minnow"
    assert result.reward == 55
    assert result.wallet == 630
    with pytest.raises(ActionCooldownError):
        await fish_service.fish(1)
    assert (await LogRepository(db).recent_games(1))[0].kind == "fish"


# ── Boss ─────────────────────────────────────────────────────────────────
async def test_boss_damage_cooldown_and_kill(db: Database) -> None:
    users = UserRepository(db)
    user = await users.get_or_create(1)
    await users.set_level_xp(1, 3, user.xp)
    service = BossService(db, users=users, rng=StubRng(int_value=200))

    status = await service.status("chrome_wyrm")
    assert status.hp == 5_000
    attack = await service.attack(1, "chrome_wyrm")
    assert attack.damage == 260  # 200 + level 3 × 20
    assert attack.killed is False
    assert attack.xp == 5
    assert (await service.status("chrome_wyrm")).hp == 4_740
    with pytest.raises(ActionCooldownError):
        await service.attack(1, "chrome_wyrm")

    await users.get_or_create(2)
    await users.set_level_xp(2, 3, 0)
    service._states["chrome_wyrm"].hp = 100
    kill = await service.attack(2, "chrome_wyrm")
    assert kill.killed is True
    assert kill.reward == 1_500
    assert kill.xp == 100
    assert kill.wallet == 2_000
    assert (await service.status("chrome_wyrm")).hp == 5_000


async def test_boss_level_gate_and_critical_strike(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    service = BossService(db, users=users, rng=StubRng(int_value=200))
    with pytest.raises(BossNotFoundError):
        await service.attack(1, "chrome_wyrm")

    await users.set_level_xp(1, 3, 0)
    skills_repo = SkillRepository(db)
    await skills_repo.set_activation(
        1,
        "critical_strike",
        last_used_at=to_db(utcnow()),
        active_until=to_db(utcnow() + timedelta(hours=1)),
    )
    attack = await service.attack(1, "chrome_wyrm", use_skill=True)
    assert attack.critical is True
    assert attack.damage == 390  # 260 × 1.5
    assert (await skills_repo.get(1, "critical_strike")).active_until is None  # type: ignore[union-attr]


async def test_boss_without_charge_rejected(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.set_level_xp(1, 3, 0)
    service = BossService(db, users=users, rng=StubRng(int_value=200))
    with pytest.raises(SkillNotUsableError):
        await service.attack(1, "chrome_wyrm", use_skill=True)


# ── Duel ─────────────────────────────────────────────────────────────────
async def _duel_setup(db: Database, *, bet: int = 100) -> tuple[DuelService, str]:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.get_or_create(2)
    service = DuelService(db, users=users, rng=StubRng(int_value=50))
    state = await service.challenge(1, 2, bet)
    state = await service.accept(state.duel_id, 2)
    return service, state.duel_id


async def test_duel_turn_based_win_and_escrow(db: Database) -> None:
    service, duel_id = await _duel_setup(db)
    users = UserRepository(db)
    assert (await users.get(1)).wallet == 400  # type: ignore[union-attr]
    assert (await users.get(2)).wallet == 400  # type: ignore[union-attr]

    state = await service.attack(duel_id, 1)
    assert state.opponent_hp == 50
    assert state.turn_id == 2
    with pytest.raises(GameStateError):
        await service.attack(duel_id, 1)

    state = await service.attack(duel_id, 2)
    assert state.challenger_hp == 50
    assert state.turn_id == 1

    state = await service.attack(duel_id, 1)
    assert state.status == "done"
    assert state.winner_id == 1
    assert state.payout == 192
    assert (await users.get(1)).wallet == 592  # type: ignore[union-attr]
    assert (await users.get(2)).wallet == 400  # type: ignore[union-attr]

    games = await LogRepository(db).recent_games(1)
    assert games[0].kind == "duel"
    assert games[0].outcome == "win"


async def test_duel_defend_and_critical(db: Database) -> None:
    service, duel_id = await _duel_setup(db)
    state = await service.attack(duel_id, 1, "defend")
    assert state.turn_id == 2
    state = await service.attack(duel_id, 2)
    assert state.challenger_hp == 75  # 50 damage → хагас

    skills_repo = SkillRepository(db)
    await skills_repo.set_activation(
        1,
        "critical_strike",
        last_used_at=to_db(utcnow()),
        active_until=to_db(utcnow() + timedelta(hours=1)),
    )
    service2, duel2 = await _duel_setup(db)
    state = await service2.attack(duel2, 1, "skill")
    assert state.opponent_hp == 25  # 50 × 1.5 = 75 damage
    assert (await skills_repo.get(1, "critical_strike")).active_until is None  # type: ignore[union-attr]


async def test_duel_decline_and_validation(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.get_or_create(2)
    service = DuelService(db, users=users)
    with pytest.raises(ValidationError):
        await service.challenge(1, 1, 100)
    with pytest.raises(InvalidBetError):
        await service.challenge(1, 2, 10)

    state = await service.challenge(1, 2, 100)
    declined = await service.decline(state.duel_id, 2)
    assert declined.status == "declined"
    assert (await users.get(1)).wallet == 500  # type: ignore[union-attr]
    assert (await users.get(2)).wallet == 500  # type: ignore[union-attr]
    with pytest.raises(GameStateError):
        await service.accept(state.duel_id, 2)


async def test_duel_accept_requires_funds(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.get_or_create(2)
    service = DuelService(db, users=users)
    state = await service.challenge(1, 2, 100)
    await users.spend_wallet(2, 450)  # 50 үлдэв
    with pytest.raises(InsufficientFundsError):
        await service.accept(state.duel_id, 2)
    assert (await users.get(1)).wallet == 500  # type: ignore[union-attr]
