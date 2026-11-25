"""Daily / Work орлого.

`Daily` нь 24 цагийн cooldown, streak bonus, Golden Touch-ийг тооцно.
`Work` нь ажлын жагсаалтаас (data/economy/jobs.json) сонгож, 30 минутын
cooldown-той цалин өгнө. XP нь `XPGained` event-ээр `LevelService` руу явна.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

import config
from core.database import Database
from core.event_bus import EventBus, XPGained
from core.exceptions import ActionCooldownError, JobNotFoundError
from core.locks import user_lock
from repositories.cooldown_repo import CooldownRepository
from repositories.log_repo import LogRepository
from repositories.user_repo import UserRepository
from services.rpg.skill_service import SkillService
from utils.data_loader import load_list
from utils.time_utils import from_db, seconds_since, to_db, utcnow


@dataclass(frozen=True, slots=True)
class JobDef:
    job_id: str
    name: str
    icon: str
    description: str
    min_level: int
    min_pay: int
    max_pay: int
    xp: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobDef:
        return cls(
            job_id=str(data["job_id"]),
            name=str(data["name"]),
            icon=str(data.get("icon", "💼")),
            description=str(data.get("description", "")),
            min_level=int(data.get("min_level", 1)),
            min_pay=int(data["min_pay"]),
            max_pay=int(data["max_pay"]),
            xp=int(data.get("xp", 10)),
        )


def load_jobs() -> list[JobDef]:
    return [JobDef.from_dict(row) for row in load_list("economy/jobs.json")]


@dataclass(frozen=True, slots=True)
class DailyResult:
    reward: int
    streak: int
    xp: int
    wallet: int
    level: int


@dataclass(frozen=True, slots=True)
class WorkResult:
    job: JobDef
    reward: int
    xp: int
    wallet: int
    cooldown_sec: int


class IncomeService:
    def __init__(
        self,
        db: Database,
        *,
        users: UserRepository | None = None,
        cooldowns: CooldownRepository | None = None,
        logs: LogRepository | None = None,
        skills: SkillService | None = None,
        level_service: Any | None = None,
        event_bus: EventBus | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.db = db
        self.users = users or UserRepository(db)
        self.cooldowns = cooldowns or CooldownRepository(db)
        self.logs = logs or LogRepository(db)
        self.skills = skills or SkillService(db, user_repo=self.users)
        self.level_service = level_service
        self.bus = event_bus
        self.rng = rng or random.Random()

    async def _award_xp(self, user_id: int, amount: int, source: str) -> None:
        if amount <= 0:
            return
        if self.bus is not None:
            await self.bus.publish(
                XPGained(user_id=user_id, amount=amount, source=source)
            )
        elif self.level_service is not None:
            await self.level_service.award_xp(user_id, amount, source=source)

    def jobs_for(self, level: int) -> list[JobDef]:
        return [job for job in load_jobs() if level >= job.min_level]

    async def daily(self, user_id: int) -> DailyResult:
        async with user_lock(user_id), self.db.transaction():
            await self.db.advisory_xact_lock(user_id)
            user = await self.users.get_or_create(user_id)
            last = user.last_daily_at
            elapsed = seconds_since(from_db(last))
            if last and elapsed < config.DAILY_COOLDOWN_SEC:
                raise ActionCooldownError("daily", config.DAILY_COOLDOWN_SEC - elapsed)
            streak = user.daily_streak + 1 if last and elapsed <= 48 * 60 * 60 else 1
            base = config.DAILY_BASE_REWARD + user.level * config.DAILY_LEVEL_BONUS
            streak_pct = min(
                streak * config.DAILY_STREAK_BONUS_PCT,
                config.DAILY_STREAK_MAX_PCT,
            )
            mods = await self.skills.get_modifiers(user_id)
            reward = mods.apply_income(int(base * (1.0 + streak_pct)))
            wallet = await self.users.credit_wallet(user_id, reward)
            await self.users.set_daily(user_id, streak, to_db(utcnow()))
            await self.logs.record_transaction(
                user_id,
                reward,
                "daily",
                wallet,
                {"streak": streak, "multiplier": mods.work_income_mult},
            )
            xp = mods.apply_xp(config.DAILY_XP)
            level = user.level

        await self._award_xp(user_id, xp, "daily")
        refreshed = await self.users.get(user_id)
        return DailyResult(
            reward=reward,
            streak=streak,
            xp=xp,
            wallet=refreshed.wallet if refreshed else wallet,
            level=refreshed.level if refreshed else level,
        )

    async def work(self, user_id: int, job_id: str | None = None) -> WorkResult:
        async with user_lock(user_id), self.db.transaction():
            user = await self.users.get_or_create(user_id)
            jobs = self.jobs_for(user.level)
            if not jobs:
                raise JobNotFoundError("✦ Танд тохирох ажил одоогоор байхгүй.")
            job = (
                self.rng.choice(jobs)
                if job_id is None
                else next(
                    (item for item in jobs if item.job_id == job_id.lower()),
                    None,
                )
            )
            if job is None:
                raise JobNotFoundError()

            remaining = await self.cooldowns.remaining(user_id, "work")
            if remaining > 0:
                raise ActionCooldownError("work", remaining)

            mods = await self.skills.get_modifiers(user_id)
            reward = mods.apply_income(self.rng.randint(job.min_pay, job.max_pay))
            xp = mods.apply_xp(job.xp)
            wallet = await self.users.credit_wallet(user_id, reward)
            await self.cooldowns.set_for(user_id, "work", config.WORK_COOLDOWN_SEC)
            await self.logs.record_transaction(
                user_id,
                reward,
                "work",
                wallet,
                {"job": job.job_id, "multiplier": mods.work_income_mult},
            )

        await self._award_xp(user_id, xp, "work")
        refreshed = await self.users.get(user_id)
        return WorkResult(
            job=job,
            reward=reward,
            xp=xp,
            wallet=refreshed.wallet if refreshed else wallet,
            cooldown_sec=config.WORK_COOLDOWN_SEC,
        )
