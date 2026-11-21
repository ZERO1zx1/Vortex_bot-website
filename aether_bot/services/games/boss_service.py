"""World Boss — нийтийн HP-тэй raid boss.

Бүх тоглогч нэг boss-ийн HP-г хамтдаа буулгана. Сүүлчийн цохилт хийсэн
тоглогч бүх шагналыг авна. Critical Strike цэнэгийг `use_skill=True`-ээр
ашиглаж, 1.5× хохирол учруулж болно.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

import config
from core.database import Database
from core.event_bus import EventBus, XPGained
from core.exceptions import (
    ActionCooldownError,
    BossNotFoundError,
    SkillNotUsableError,
)
from core.locks import user_lock
from repositories.cooldown_repo import CooldownRepository
from repositories.log_repo import LogRepository
from repositories.user_repo import UserRepository
from services.economy.wallet_service import WalletService
from services.rpg.skill_service import SkillService
from utils.data_loader import load_dict


@dataclass(frozen=True, slots=True)
class BossDef:
    boss_id: str
    name: str
    icon: str
    description: str
    min_level: int
    hp: int
    attack: int
    coin_reward: int
    xp_reward: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BossDef:
        return cls(
            boss_id=str(data["boss_id"]),
            name=str(data["name"]),
            icon=str(data.get("icon", "👹")),
            description=str(data.get("description", "")),
            min_level=int(data.get("min_level", 1)),
            hp=int(data["hp"]),
            attack=int(data.get("attack", 0)),
            coin_reward=int(data["coin_reward"]),
            xp_reward=int(data["xp_reward"]),
        )


def load_bosses() -> list[BossDef]:
    return [BossDef.from_dict(row) for row in load_dict("rpg/bosses.json")["bosses"]]


@dataclass(slots=True)
class _Runtime:
    boss: BossDef
    hp: int


@dataclass(frozen=True, slots=True)
class BossStatus:
    boss: BossDef
    hp: int
    max_hp: int

    @property
    def percent(self) -> float:
        return min(100.0, self.hp / self.max_hp * 100.0) if self.max_hp else 0.0


@dataclass(frozen=True, slots=True)
class BossAttack:
    boss: BossDef
    damage: int
    hp_left: int
    killed: bool
    reward: int
    xp: int
    wallet: int
    cooldown_sec: int
    critical: bool


class BossService:
    def __init__(
        self,
        db: Database,
        *,
        users: UserRepository | None = None,
        logs: LogRepository | None = None,
        cooldowns: CooldownRepository | None = None,
        wallet: WalletService | None = None,
        skills: SkillService | None = None,
        event_bus: EventBus | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.db = db
        self.users = users or UserRepository(db)
        self.logs = logs or LogRepository(db)
        self.cooldowns = cooldowns or CooldownRepository(db)
        self.wallet = wallet or WalletService(db, users=self.users, logs=self.logs)
        self.skills = skills or SkillService(db, user_repo=self.users)
        self.bus = event_bus
        self.rng = rng or random.Random()
        self._states: dict[str, _Runtime] = {}

    def _runtime(self, boss_id: str) -> _Runtime:
        runtime = self._states.get(boss_id)
        if runtime is None:
            boss = next(
                (item for item in load_bosses() if item.boss_id == boss_id.lower()),
                None,
            )
            if boss is None:
                raise BossNotFoundError()
            runtime = self._states[boss_id] = _Runtime(boss=boss, hp=boss.hp)
        return runtime

    @staticmethod
    def bosses_for(level: int) -> list[BossDef]:
        return [boss for boss in load_bosses() if level >= boss.min_level]

    async def status(self, boss_id: str) -> BossStatus:
        runtime = self._runtime(boss_id)
        return BossStatus(boss=runtime.boss, hp=runtime.hp, max_hp=runtime.boss.hp)

    async def attack(
        self, user_id: int, boss_id: str, *, use_skill: bool = False
    ) -> BossAttack:
        async with user_lock("boss"), user_lock(user_id), self.db.transaction():
            user = await self.users.get_or_create(user_id)
            runtime = self._runtime(boss_id)
            if user.level < runtime.boss.min_level:
                raise BossNotFoundError()
            remaining = await self.cooldowns.remaining(user_id, "boss")
            if remaining > 0:
                raise ActionCooldownError("boss", remaining)

            critical = False
            damage = self.rng.randint(150, 300) + user.level * 20
            if use_skill:
                if not await self.skills.consume_charge(user_id, "critical_strike"):
                    raise SkillNotUsableError("✦ Critical Strike цэнэг идэвхгүй байна.")
                damage = int(damage * 1.5)
                critical = True

            runtime.hp = max(0, runtime.hp - damage)
            killed = runtime.hp == 0
            reward = 0
            xp = 5
            wallet = user.wallet
            if killed:
                reward = runtime.boss.coin_reward
                xp = runtime.boss.xp_reward
                wallet = await self.wallet.credit(
                    user_id,
                    reward,
                    "boss_kill",
                    metadata={"boss": runtime.boss.boss_id},
                )
                runtime.hp = runtime.boss.hp  # шинэ boss spawn
            await self.cooldowns.set_for(user_id, "boss", config.BOSS_COOLDOWN_SEC)
            await self.logs.record_game(
                "boss",
                user_id,
                "win",
                reward_coin=reward,
                reward_xp=xp,
                detail={
                    "boss": runtime.boss.boss_id,
                    "damage": damage,
                    "critical": critical,
                },
            )

        if self.bus is not None:
            await self.bus.publish(XPGained(user_id=user_id, amount=xp, source="boss"))
        return BossAttack(
            boss=runtime.boss,
            damage=damage,
            hp_left=runtime.hp,
            killed=killed,
            reward=reward,
            xp=xp,
            wallet=wallet,
            cooldown_sec=config.BOSS_COOLDOWN_SEC,
            critical=critical,
        )
