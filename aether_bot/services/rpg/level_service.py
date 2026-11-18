"""Level / XP service.

`required_xp(level) = int(100 * level ** 1.5)`. Түвшин ахих бүрт +2 SP болон
`level * 200` Coin олгоно. `XPGained` event-ийг сонсож, `LevelUp` нийтэлнэ.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import config
from core.database import Database
from core.event_bus import EventBus, LevelUp, MoneyChanged, XPGained
from core.locks import user_lock
from repositories.log_repo import LogRepository
from repositories.shop_repo import ShopRepository
from repositories.user_repo import UserRepository


@dataclass(frozen=True, slots=True)
class LevelResult:
    user_id: int
    previous_level: int
    new_level: int
    xp_gained: int
    xp_remaining: int
    skill_points_awarded: int
    coins_awarded: int


@dataclass(frozen=True, slots=True)
class LevelProgress:
    user_id: int
    level: int
    xp: int
    required_xp: int

    @property
    def percent(self) -> float:
        if self.required_xp <= 0:
            return 100.0
        return min(100.0, self.xp / self.required_xp * 100.0)


class LevelService:
    def __init__(
        self,
        db: Database,
        *,
        users: UserRepository | None = None,
        logs: LogRepository | None = None,
        shop: ShopRepository | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.db = db
        self.users = users or UserRepository(db)
        self.logs = logs or LogRepository(db)
        self.shop = shop or ShopRepository(db)
        self.bus = event_bus

    @staticmethod
    def required_xp(level: int) -> int:
        return int(100 * (max(1, level) ** 1.5))

    def subscribe(self, bus: EventBus) -> None:
        """`XPGained` event-ийг LevelService-д холбоно."""
        bus.subscribe(XPGained, self.handle_xp_gained)
        self.bus = bus

    async def handle_xp_gained(self, event: XPGained) -> None:
        await self.award_xp(
            event.user_id,
            event.amount,
            source=event.source,
            multiplier=event.multiplier,
        )

    async def award_xp(
        self,
        user_id: int,
        amount: int,
        *,
        source: str = "xp",
        multiplier: float = 1.0,
    ) -> LevelResult:
        if amount < 0:
            raise ValueError("amount >= 0 байх ёстой")

        async with user_lock(user_id), self.db.transaction():
            user = await self.users.get_or_create(user_id)
            effect = await self.shop.effect_value(user_id, "xp_boost")
            gained = max(0, math.floor(amount * max(1.0, effect) * multiplier + 0.5))
            xp = user.xp + gained
            level = user.level
            sp_awarded = 0
            coins_awarded = 0
            while level < config.MAX_LEVEL and xp >= self.required_xp(level):
                xp -= self.required_xp(level)
                level += 1
                sp_awarded += config.LEVEL_SKILL_POINTS
                coins_awarded += level * config.LEVEL_COIN_REWARD_MULT

            if sp_awarded:
                await self.users.grant_skill_points(user_id, sp_awarded)
            if coins_awarded:
                wallet = await self.users.credit_wallet(user_id, coins_awarded)
                await self.logs.record_transaction(
                    user_id,
                    coins_awarded,
                    "level_up",
                    wallet,
                    {"level": level},
                )
            if level != user.level or xp != user.xp:
                await self.users.set_level_xp(user_id, level, xp)

        result = LevelResult(
            user_id=user_id,
            previous_level=user.level,
            new_level=level,
            xp_gained=gained,
            xp_remaining=xp,
            skill_points_awarded=sp_awarded,
            coins_awarded=coins_awarded,
        )
        if self.bus is not None:
            if level > user.level:
                await self.bus.publish(
                    LevelUp(
                        user_id=user_id,
                        previous_level=user.level,
                        new_level=level,
                        skill_points_awarded=sp_awarded,
                        coins_awarded=coins_awarded,
                    )
                )
            if coins_awarded:
                refreshed = await self.users.get(user_id)
                await self.bus.publish(
                    MoneyChanged(
                        user_id=user_id,
                        amount=coins_awarded,
                        source="level_up",
                        wallet_after=refreshed.wallet if refreshed else 0,
                        bank_after=refreshed.bank if refreshed else 0,
                    )
                )
        return result

    async def progress(self, user_id: int) -> LevelProgress:
        user = await self.users.get_or_create(user_id)
        return LevelProgress(
            user_id=user_id,
            level=user.level,
            xp=user.xp,
            required_xp=self.required_xp(user.level),
        )
