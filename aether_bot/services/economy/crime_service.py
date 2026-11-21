"""Crime ба Rob.

Амжилттай crime нь reward + XP, бүтэлгүйтвэл торгууль + шорон. `rob` нь
зорилтын Wallet-ийн 10–30%-ийг хулгайлж чадна; Aether Shield эсвэл
`shield_until` идэвхтэй бол хамгаалагдсан. Shadow Step нь rob-ийн
амжилтыг нэмэгдүүлж, баригдвал торгууль болон шоронгийн хугацааг бууруулна.
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
    CrimeNotFoundError,
    JailedError,
    TargetProtectedError,
    ValidationError,
)
from core.locks import multi_user_lock, user_lock
from repositories.cooldown_repo import CooldownRepository
from repositories.log_repo import LogRepository
from repositories.user_repo import UserRepository
from services.economy.jail_service import JailService
from services.rpg.skill_service import SkillService
from utils.data_loader import load_list
from utils.time_utils import from_db, seconds_until, utcnow


@dataclass(frozen=True, slots=True)
class CrimeDef:
    crime_id: str
    name: str
    icon: str
    description: str
    min_level: int
    success_chance: float
    min_reward: int
    max_reward: int
    min_fine: int
    max_fine: int
    jail_minutes: int
    bail_cost: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CrimeDef:
        return cls(
            crime_id=str(data["crime_id"]),
            name=str(data["name"]),
            icon=str(data.get("icon", "🕶️")),
            description=str(data.get("description", "")),
            min_level=int(data.get("min_level", 1)),
            success_chance=float(data["success_chance"]),
            min_reward=int(data["min_reward"]),
            max_reward=int(data["max_reward"]),
            min_fine=int(data["min_fine"]),
            max_fine=int(data["max_fine"]),
            jail_minutes=int(data["jail_minutes"]),
            bail_cost=int(data["bail_cost"]),
        )


def load_crimes() -> list[CrimeDef]:
    return [CrimeDef.from_dict(row) for row in load_list("economy/crimes.json")]


@dataclass(frozen=True, slots=True)
class CrimeResult:
    crime: CrimeDef
    success: bool
    reward: int
    fine: int
    xp: int
    wallet: int
    jailed: bool
    jail_until: str | None


@dataclass(frozen=True, slots=True)
class RobResult:
    success: bool
    stolen: int
    fine: int
    xp: int
    actor_wallet: int
    target_wallet: int
    jailed: bool
    jail_until: str | None


class CrimeService:
    def __init__(
        self,
        db: Database,
        *,
        users: UserRepository | None = None,
        cooldowns: CooldownRepository | None = None,
        logs: LogRepository | None = None,
        skills: SkillService | None = None,
        jail: JailService | None = None,
        event_bus: EventBus | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.db = db
        self.users = users or UserRepository(db)
        self.cooldowns = cooldowns or CooldownRepository(db)
        self.logs = logs or LogRepository(db)
        self.skills = skills or SkillService(db, user_repo=self.users)
        self.jail = jail or JailService(
            db, users=self.users, skills=self.skills, event_bus=event_bus
        )
        self.bus = event_bus
        self.rng = rng or random.Random()

    def crimes_for(self, level: int) -> list[CrimeDef]:
        return [crime for crime in load_crimes() if level >= crime.min_level]

    async def _award_xp(self, user_id: int, amount: int, source: str) -> None:
        if amount > 0 and self.bus is not None:
            await self.bus.publish(
                XPGained(user_id=user_id, amount=amount, source=source)
            )

    def _raise_if_jailed(self, user: Any) -> None:
        until = from_db(user.jail_until)
        if until is not None and until > utcnow():
            raise JailedError(seconds_until(until), user.jail_bail_cost)

    async def crime(self, user_id: int, crime_id: str) -> CrimeResult:
        async with user_lock(user_id), self.db.transaction():
            user = await self.users.get_or_create(user_id)
            self._raise_if_jailed(user)

            remaining = await self.cooldowns.remaining(user_id, "crime")
            if remaining > 0:
                raise ActionCooldownError("crime", remaining)

            crime = next(
                (
                    item
                    for item in self.crimes_for(user.level)
                    if item.crime_id == crime_id.lower()
                ),
                None,
            )
            if crime is None:
                raise CrimeNotFoundError()

            success = self.rng.random() < crime.success_chance
            reward = 0
            fine = 0
            xp = 0
            if success:
                reward = self.rng.randint(crime.min_reward, crime.max_reward)
                wallet = await self.users.credit_wallet(user_id, reward)
                await self.logs.record_transaction(
                    user_id, reward, "crime", wallet, {"crime": crime.crime_id}
                )
                xp = 15 + crime.min_level * 2
            else:
                fine = min(
                    user.wallet,
                    self.rng.randint(crime.min_fine, crime.max_fine),
                )
                if fine > 0:
                    await self.users.spend_wallet(user_id, fine)
                wallet = (await self.users.get(user_id)).wallet  # type: ignore[union-attr]
                if fine > 0:
                    await self.logs.record_transaction(
                        user_id,
                        -fine,
                        "crime_fine",
                        wallet,
                        {"crime": crime.crime_id},
                    )
                xp = 5

            await self.cooldowns.set_for(user_id, "crime", config.CRIME_COOLDOWN_SEC)

        jailed = False
        jail_until: str | None = None
        if not success:
            jail_result = await self.jail.imprison(
                user_id,
                minutes=crime.jail_minutes,
                bail_cost=crime.bail_cost,
                reason=f"crime:{crime.crime_id}",
            )
            jailed = True
            jail_until = jail_result.until

        await self._award_xp(user_id, xp, "crime")
        return CrimeResult(
            crime=crime,
            success=success,
            reward=reward,
            fine=fine,
            xp=xp,
            wallet=wallet,
            jailed=jailed,
            jail_until=jail_until,
        )

    async def rob(self, actor_id: int, target_id: int) -> RobResult:
        if actor_id == target_id:
            raise ValidationError("✦ Өөрийгөө тонож болохгүй.")

        async with multi_user_lock(actor_id, target_id), self.db.transaction():
            actor = await self.users.get_or_create(actor_id)
            target = await self.users.get_or_create(target_id)
            self._raise_if_jailed(actor)

            remaining = await self.cooldowns.remaining(actor_id, "rob")
            if remaining > 0:
                raise ActionCooldownError("rob", remaining)

            shield_until = from_db(target.shield_until)
            target_mods = await self.skills.get_modifiers(target_id)
            if (shield_until is not None and shield_until > utcnow()) or (
                target_mods.shield_active
            ):
                raise TargetProtectedError()

            if target.wallet <= 0:
                raise ValidationError("✦ Зорилтын Wallet хоосон байна.")

            actor_mods = await self.skills.get_modifiers(actor_id)
            success = self.rng.random() < actor_mods.rob_success_chance()
            stolen = 0
            fine = 0
            xp = 0

            if success:
                stolen = max(
                    1,
                    int(
                        target.wallet * self.rng.uniform(0.10, config.ROB_MAX_STEAL_PCT)
                    ),
                )
                stolen = min(stolen, target.wallet)
                await self.users.spend_wallet(target_id, stolen)
                actor_wallet = await self.users.credit_wallet(actor_id, stolen)
                target_wallet = (await self.users.get(target_id)).wallet  # type: ignore[union-attr]
                await self.logs.record_transaction(
                    actor_id,
                    stolen,
                    "rob",
                    actor_wallet,
                    {"target": target_id},
                )
                await self.logs.record_transaction(
                    target_id,
                    -stolen,
                    "robbed",
                    target_wallet,
                    {"actor": actor_id},
                )
                xp = 25
            else:
                fine = min(
                    actor.wallet,
                    int(actor.wallet * config.ROB_FINE_PCT * actor_mods.rob_fine_mult),
                )
                if fine > 0:
                    await self.users.spend_wallet(actor_id, fine)
                actor_wallet = (await self.users.get(actor_id)).wallet  # type: ignore[union-attr]
                target_wallet = target.wallet
                if fine > 0:
                    await self.logs.record_transaction(
                        actor_id,
                        -fine,
                        "rob_fine",
                        actor_wallet,
                        {"target": target_id},
                    )
                xp = 5

            await self.cooldowns.set_for(actor_id, "rob", config.ROB_COOLDOWN_SEC)

        jailed = False
        jail_until: str | None = None
        if not success:
            jail_result = await self.jail.imprison(
                actor_id,
                minutes=config.ROB_JAIL_MINUTES,
                bail_cost=config.ROB_JAIL_BAIL,
                reason="rob_failed",
            )
            jailed = True
            jail_until = jail_result.until

        await self._award_xp(actor_id, xp, "rob")
        return RobResult(
            success=success,
            stolen=stolen,
            fine=fine,
            xp=xp,
            actor_wallet=actor_wallet,
            target_wallet=target_wallet,
            jailed=jailed,
            jail_until=jail_until,
        )
