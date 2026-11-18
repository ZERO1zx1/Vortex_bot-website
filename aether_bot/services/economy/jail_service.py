"""Jail: хорих, хугацаа шалгах, батлан даалтаар гарах.

Shadow Step нь `Modifiers.jail_reduction_pct`-ээр дамжуулан хорих хугацаа
болон bail үнийг хоёуланг нь бууруулна (түвшин бүрт 5%, дээд тал нь 25%).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta

import config
from core.database import Database
from core.event_bus import EventBus, UserJailed, UserReleased
from core.exceptions import (
    InsufficientFundsError,
    JailedError,
    NotJailedError,
    ValidationError,
)
from core.locks import user_lock
from repositories.log_repo import LogRepository
from repositories.user_repo import UserRepository
from services.rpg.skill_service import SkillService
from utils.time_utils import from_db, seconds_until, to_db, utcnow


@dataclass(frozen=True, slots=True)
class JailStatus:
    user_id: int
    jailed: bool
    until: str | None
    remaining_sec: int
    bail_cost: int


@dataclass(frozen=True, slots=True)
class JailResult:
    user_id: int
    until: str
    minutes: int
    bail_cost: int
    reason: str


class JailService:
    def __init__(
        self,
        db: Database,
        *,
        users: UserRepository | None = None,
        logs: LogRepository | None = None,
        skills: SkillService | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.db = db
        self.users = users or UserRepository(db)
        self.logs = logs or LogRepository(db)
        self.skills = skills or SkillService(db, user_repo=self.users)
        self.bus = event_bus

    async def status(self, user_id: int) -> JailStatus:
        user = await self.users.get_or_create(user_id)
        until = from_db(user.jail_until)
        remaining = seconds_until(until)
        jailed = until is not None and remaining > 0
        return JailStatus(
            user_id=user_id,
            jailed=jailed,
            until=user.jail_until if jailed else None,
            remaining_sec=remaining if jailed else 0,
            bail_cost=user.jail_bail_cost if jailed else 0,
        )

    async def ensure_not_jailed(self, user_id: int) -> None:
        status = await self.status(user_id)
        if status.jailed:
            raise JailedError(status.remaining_sec, status.bail_cost)

    async def imprison(
        self,
        user_id: int,
        *,
        minutes: int,
        bail_cost: int,
        reason: str = "crime",
    ) -> JailResult:
        if minutes <= 0:
            raise ValidationError("✦ Хорих хугацаа 0-ээс их байх ёстой.")
        if bail_cost < 0:
            raise ValidationError()

        async with user_lock(user_id), self.db.transaction():
            user = await self.users.get_or_create(user_id)
            mods = await self.skills.get_modifiers(user_id)
            effective_minutes = max(1, math.ceil(minutes * mods.jail_time_mult))
            effective_bail = (
                max(1, math.floor(bail_cost * mods.jail_time_mult))
                if bail_cost > 0
                else 0
            )
            now = utcnow()
            existing = from_db(user.jail_until)
            start = existing if existing and existing > now else now
            until = start + timedelta(
                minutes=min(effective_minutes, config.JAIL_MAX_MINUTES)
            )
            await self.users.set_jail(
                user_id, until=to_db(until), bail_cost=effective_bail
            )

        result = JailResult(
            user_id=user_id,
            until=to_db(until),
            minutes=effective_minutes,
            bail_cost=effective_bail,
            reason=reason,
        )
        if self.bus is not None:
            await self.bus.publish(
                UserJailed(
                    user_id=user_id,
                    until=until,
                    bail_cost=effective_bail,
                    reason=reason,
                )
            )
        return result

    async def bail(self, user_id: int) -> JailResult:
        async with user_lock(user_id), self.db.transaction():
            user = await self.users.get_or_create(user_id)
            until = from_db(user.jail_until)
            remaining = seconds_until(until)
            if until is None or remaining <= 0:
                raise NotJailedError()
            cost = user.jail_bail_cost
            if cost > 0 and not await self.users.spend_wallet(user_id, cost):
                raise InsufficientFundsError(
                    f"✦ Батлан даалтын **{cost:,}** ⛃ хүрэлцэхгүй байна."
                )
            wallet = (await self.users.get(user_id)).wallet  # type: ignore[union-attr]
            await self.users.clear_jail(user_id)
            if cost > 0:
                await self.logs.record_transaction(user_id, -cost, "bail", wallet)

        result = JailResult(
            user_id=user_id,
            until=to_db(utcnow()),
            minutes=0,
            bail_cost=cost,
            reason="bail",
        )
        if self.bus is not None:
            await self.bus.publish(UserReleased(user_id=user_id, reason="bail"))
        return result

    async def release_if_expired(self, user_id: int) -> bool:
        async with user_lock(user_id), self.db.transaction():
            user = await self.users.get(user_id)
            if user is None or user.jail_until is None:
                return False
            until = from_db(user.jail_until)
            if until is not None and until > utcnow():
                return False
            await self.users.clear_jail(user_id)
        if self.bus is not None:
            await self.bus.publish(UserReleased(user_id=user_id, reason="expired"))
        return True
