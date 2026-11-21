"""Adventure — dungeon сонгож, эрсдэлтэй олз олох.

Dungeon бүр `min_level`, `danger` (бүтэлгүйтэх магадлал) болон шагналын
хязгаартай. Cooldown нь `cooldowns` хүснэгтэд хадгалагдана.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

import config
from core.database import Database
from core.event_bus import EventBus, XPGained
from core.exceptions import ActionCooldownError, DungeonNotFoundError
from core.locks import user_lock
from repositories.cooldown_repo import CooldownRepository
from repositories.log_repo import LogRepository
from repositories.user_repo import UserRepository
from services.economy.wallet_service import WalletService
from utils.data_loader import load_dict


@dataclass(frozen=True, slots=True)
class DungeonDef:
    dungeon_id: str
    name: str
    icon: str
    description: str
    min_level: int
    danger: float
    min_reward: int
    max_reward: int
    xp: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DungeonDef:
        return cls(
            dungeon_id=str(data["dungeon_id"]),
            name=str(data["name"]),
            icon=str(data.get("icon", "🏚️")),
            description=str(data.get("description", "")),
            min_level=int(data.get("min_level", 1)),
            danger=float(data.get("danger", 0.0)),
            min_reward=int(data["min_reward"]),
            max_reward=int(data["max_reward"]),
            xp=int(data.get("xp", 10)),
        )


def load_dungeons() -> list[DungeonDef]:
    return [
        DungeonDef.from_dict(row) for row in load_dict("rpg/dungeons.json")["dungeons"]
    ]


@dataclass(frozen=True, slots=True)
class AdventureResult:
    dungeon: DungeonDef
    success: bool
    reward: int
    xp: int
    wallet: int
    cooldown_sec: int
    message: str


class AdventureService:
    def __init__(
        self,
        db: Database,
        *,
        users: UserRepository | None = None,
        logs: LogRepository | None = None,
        cooldowns: CooldownRepository | None = None,
        wallet: WalletService | None = None,
        event_bus: EventBus | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.db = db
        self.users = users or UserRepository(db)
        self.logs = logs or LogRepository(db)
        self.cooldowns = cooldowns or CooldownRepository(db)
        self.wallet = wallet or WalletService(db, users=self.users, logs=self.logs)
        self.bus = event_bus
        self.rng = rng or random.Random()

    @staticmethod
    def dungeons_for(level: int) -> list[DungeonDef]:
        return [dungeon for dungeon in load_dungeons() if level >= dungeon.min_level]

    async def explore(self, user_id: int, dungeon_id: str) -> AdventureResult:
        dungeon = next(
            (item for item in load_dungeons() if item.dungeon_id == dungeon_id.lower()),
            None,
        )
        async with user_lock(user_id), self.db.transaction():
            user = await self.users.get_or_create(user_id)
            if dungeon is None or user.level < dungeon.min_level:
                raise DungeonNotFoundError()
            remaining = await self.cooldowns.remaining(user_id, "adventure")
            if remaining > 0:
                raise ActionCooldownError("adventure", remaining)

            success = self.rng.random() >= dungeon.danger
            reward = (
                self.rng.randint(dungeon.min_reward, dungeon.max_reward)
                if success
                else 0
            )
            xp = dungeon.xp if success else 5
            wallet = user.wallet
            if reward > 0:
                wallet = await self.wallet.credit(
                    user_id,
                    reward,
                    "adventure",
                    metadata={"dungeon": dungeon.dungeon_id},
                )
            await self.cooldowns.set_for(
                user_id, "adventure", config.ADVENTURE_COOLDOWN_SEC
            )
            await self.logs.record_game(
                "adventure",
                user_id,
                "win" if success else "loss",
                reward_coin=reward,
                reward_xp=xp,
                detail={"dungeon": dungeon.dungeon_id},
            )

        if xp > 0 and self.bus is not None:
            await self.bus.publish(
                XPGained(user_id=user_id, amount=xp, source="adventure")
            )
        return AdventureResult(
            dungeon=dungeon,
            success=success,
            reward=reward,
            xp=xp,
            wallet=wallet,
            cooldown_sec=config.ADVENTURE_COOLDOWN_SEC,
            message=(
                f"✦ **{dungeon.name}**-ыг амжилттай гатлав."
                if success
                else f"✦ **{dungeon.name}**-д баригдлаа."
            ),
        )
