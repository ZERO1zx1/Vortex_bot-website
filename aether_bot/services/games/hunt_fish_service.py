"""Hunt ба Fish — cooldown-той мини азын тоглоом.

Хоёулаа ижил механиктай: жинтэй хүснэгтээс олз сонгож, Coin болон XP өгнө.
Ялгаа нь хүснэгт, cooldown, логны `kind` төрөл.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

import config
from core.database import Database
from core.event_bus import EventBus, XPGained
from core.exceptions import ActionCooldownError
from core.locks import user_lock
from repositories.cooldown_repo import CooldownRepository
from repositories.log_repo import LogRepository
from repositories.user_repo import UserRepository
from services.economy.wallet_service import WalletService

HUNT_TABLE: tuple[dict[str, Any], ...] = (
    {
        "name": "Neon Rabbit",
        "icon": "🐇",
        "weight": 35,
        "min": 60,
        "max": 120,
        "xp": 10,
    },
    {"name": "Cyber Fox", "icon": "🦊", "weight": 25, "min": 120, "max": 220, "xp": 16},
    {
        "name": "Plasma Boar",
        "icon": "🐗",
        "weight": 18,
        "min": 220,
        "max": 380,
        "xp": 24,
    },
    {
        "name": "Astral Stag",
        "icon": "🦌",
        "weight": 12,
        "min": 380,
        "max": 600,
        "xp": 34,
    },
    {
        "name": "Void Panther",
        "icon": "🐆",
        "weight": 7,
        "min": 650,
        "max": 1_000,
        "xp": 48,
    },
    {
        "name": "Chrome Dragonling",
        "icon": "🐲",
        "weight": 3,
        "min": 1_200,
        "max": 2_000,
        "xp": 80,
    },
)

FISH_TABLE: tuple[dict[str, Any], ...] = (
    {"name": "Rust Minnow", "icon": "🐟", "weight": 35, "min": 50, "max": 100, "xp": 8},
    {"name": "Neon Koi", "icon": "🎏", "weight": 25, "min": 100, "max": 190, "xp": 14},
    {
        "name": "Aether Eel",
        "icon": "🐍",
        "weight": 18,
        "min": 190,
        "max": 340,
        "xp": 22,
    },
    {
        "name": "Crystal Trout",
        "icon": "💠",
        "weight": 12,
        "min": 340,
        "max": 560,
        "xp": 32,
    },
    {
        "name": "Abyss Whale",
        "icon": "🐋",
        "weight": 7,
        "min": 600,
        "max": 950,
        "xp": 46,
    },
    {
        "name": "Star Leviathan",
        "icon": "🌌",
        "weight": 3,
        "min": 1_100,
        "max": 1_800,
        "xp": 75,
    },
)


@dataclass(frozen=True, slots=True)
class CatchResult:
    kind: str
    catch: str
    icon: str
    reward: int
    xp: int
    wallet: int
    cooldown_sec: int


class HuntFishService:
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

    async def hunt(self, user_id: int) -> CatchResult:
        return await self._act(
            user_id,
            kind="hunt",
            table=HUNT_TABLE,
            cooldown=config.HUNT_COOLDOWN_SEC,
        )

    async def fish(self, user_id: int) -> CatchResult:
        return await self._act(
            user_id,
            kind="fish",
            table=FISH_TABLE,
            cooldown=config.FISH_COOLDOWN_SEC,
        )

    async def _act(
        self,
        user_id: int,
        *,
        kind: str,
        table: tuple[dict[str, Any], ...],
        cooldown: int,
    ) -> CatchResult:
        async with user_lock(user_id), self.db.transaction():
            await self.users.get_or_create(user_id)
            remaining = await self.cooldowns.remaining(user_id, kind)
            if remaining > 0:
                raise ActionCooldownError(kind, remaining)
            entry = self.rng.choices(
                table, weights=[row["weight"] for row in table], k=1
            )[0]
            reward = self.rng.randint(int(entry["min"]), int(entry["max"]))
            xp = int(entry["xp"])
            wallet = await self.wallet.credit(
                user_id,
                reward,
                kind,
                metadata={"catch": entry["name"]},
            )
            await self.cooldowns.set_for(user_id, kind, cooldown)
            await self.logs.record_game(
                kind,
                user_id,
                "win",
                reward_coin=reward,
                reward_xp=xp,
                detail={"catch": entry["name"]},
            )

        if self.bus is not None:
            await self.bus.publish(XPGained(user_id=user_id, amount=xp, source=kind))
        return CatchResult(
            kind=kind,
            catch=str(entry["name"]),
            icon=str(entry["icon"]),
            reward=reward,
            xp=xp,
            wallet=wallet,
            cooldown_sec=cooldown,
        )
