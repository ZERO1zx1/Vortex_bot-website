"""SkillService — бүх модулийн бонусыг тооцоолох цорын ганц эх сурвалж.

Бусад service (Economy, Casino, Shop, Game, Level) тооцоолол хийхээс өмнө
`await skill_service.get_modifiers(user_id)` дуудаж нэгдсэн modifier авна.
Ингэснээр skill-ийн нөлөө хаа сайгүй ижил бодогдоно, модуль бүрт давхар
томьёо бичихгүй.

Гурван үйлдэл:
- `upgrade()` — SP зарцуулж түвшин нэмнэ (atomic, per-user lock).
- `activate()` — Active skill-ийг cooldown шалгаад идэвхжүүлнэ.
- `consume_charge()` — нэг удаагийн эффектийг (Critical Strike) зарцуулна.
- `reset()` — Tome of Rebirth хэрэглэсний дараа бүх skill-ийг буцаана.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta

import config
from core.database import Database
from core.event_bus import EventBus, SkillActivated, SkillUpgraded
from core.exceptions import (
    CooldownError,
    InsufficientSkillPointsError,
    SkillLockedError,
    SkillMaxedError,
    SkillNotActiveTypeError,
    SkillNotFoundError,
    SkillNotUsableError,
)
from core.locks import user_lock
from core.skill_catalog import (
    ACTIVE,
    PATHS,
    SKILLS,
    SkillDef,
    get_skill,
    skills_by_path,
)
from repositories.skill_repo import SkillRepository, SkillRow
from repositories.user_repo import UserRepository
from utils.time_utils import (
    from_db,
    humanize_seconds,
    seconds_since,
    seconds_until,
    to_db,
    utcnow,
)

log = logging.getLogger(__name__)

# Modifiers-ийг богино хугацаанд кэшлэх — нэг командад 3-4 удаа дуудагддаг.
_LEVEL_CACHE_TTL = 15.0


def _is_active(value: str | None) -> bool:
    """`active_until` текст одооноос хойш байна уу?"""
    moment = from_db(value)
    return moment is not None and moment > utcnow()


def _round_half_up(value: float) -> int:
    """Banker's rounding биш, тогтвортой 0.5-дээш дугуйруулна."""
    return math.floor(value + 0.5)


# ── Үр дүнгийн бүтцүүд ───────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class Modifiers:
    """Бүх сервисийн хүлээж авдаг нэгдсэн бонус багц."""

    work_income_mult: float = 1.0
    casino_cashback_pct: float = 0.0
    shop_discount_pct: float = 0.0
    rob_success_bonus: float = 0.0
    rob_fine_mult: float = 1.0
    xp_gain_mult: float = 1.0
    crit_active: bool = False
    shield_active: bool = False

    def as_dict(self) -> dict[str, float | bool]:
        return {
            "work_income_mult": round(self.work_income_mult, 4),
            "casino_cashback_pct": round(self.casino_cashback_pct, 4),
            "shop_discount_pct": round(self.shop_discount_pct, 4),
            "rob_success_bonus": round(self.rob_success_bonus, 4),
            "rob_fine_mult": round(self.rob_fine_mult, 4),
            "xp_gain_mult": round(self.xp_gain_mult, 4),
            "crit_active": self.crit_active,
            "shield_active": self.shield_active,
        }

    # ── Service-үүдэд зориулсан бэлэн туслахууд ──────────────────────
    def apply_income(self, amount: int) -> int:
        """`/daily`, `/work`-ийн орлогод Golden Touch-ийг хэрэглэнэ."""
        return max(0, _round_half_up(amount * self.work_income_mult))

    def apply_xp(self, amount: int) -> int:
        return max(0, _round_half_up(amount * self.xp_gain_mult))

    def discounted_price(self, price: int) -> int:
        if price <= 0:
            return 0
        # Хямдрал нь тоглогчийн талд дугуйрна (дээш биш).
        return max(1, math.floor(price * (1.0 - self.shop_discount_pct)))

    def cashback(self, lost_bet: int) -> int:
        if lost_bet <= 0 or self.casino_cashback_pct <= 0:
            return 0
        return _round_half_up(lost_bet * self.casino_cashback_pct)

    def rob_success_chance(self, base: float = config.ROB_BASE_SUCCESS) -> float:
        """Хожих магадлал 92%-иас хэтрэхгүй (эдийн засгийн хамгаалалт)."""
        return min(0.92, base + self.rob_success_bonus)


@dataclass(frozen=True, slots=True)
class SkillState:
    skill: SkillDef
    level: int
    last_used_at: datetime | None
    active_until: datetime | None

    @property
    def is_owned(self) -> bool:
        return self.level > 0

    @property
    def is_active(self) -> bool:
        return self.active_until is not None and self.active_until > utcnow()

    @property
    def cooldown_remaining(self) -> int:
        if not self.last_used_at or self.skill.cooldown_sec <= 0:
            return 0
        elapsed = seconds_since(self.last_used_at)
        return max(0, self.skill.cooldown_sec - elapsed)


@dataclass(frozen=True, slots=True)
class SkillTree:
    user_id: int
    skill_points: int
    level: int
    paths: dict[str, list[SkillState]]

    @property
    def total_levels(self) -> int:
        return sum(state.level for states in self.paths.values() for state in states)


@dataclass(frozen=True, slots=True)
class UpgradeResult:
    skill: SkillDef
    previous_level: int
    new_level: int
    skill_points_left: int

    @property
    def maxed(self) -> bool:
        return self.new_level >= self.skill.max_level


@dataclass(frozen=True, slots=True)
class ActivationResult:
    skill: SkillDef
    active_until: datetime
    cooldown_sec: int


@dataclass(frozen=True, slots=True)
class ResetResult:
    refunded_points: int
    skill_points: int


# ── Service ──────────────────────────────────────────────────────────────
class SkillService:
    def __init__(
        self,
        db: Database,
        *,
        user_repo: UserRepository | None = None,
        skill_repo: SkillRepository | None = None,
        event_bus: EventBus | None = None,
        cache_ttl: float = _LEVEL_CACHE_TTL,
    ) -> None:
        self.db = db
        self.users = user_repo or UserRepository(db)
        self.skills = skill_repo or SkillRepository(db)
        self.bus = event_bus
        self.cache_ttl = cache_ttl
        # user_id -> (expires_at_monotonic, {skill_id: SkillRow})
        self._levels_cache: dict[int, tuple[float, dict[str, SkillRow]]] = {}

    # ── Унших ─────────────────────────────────────────────────────────
    async def _load_levels(self, user_id: int) -> dict[str, SkillRow]:
        now = utcnow().timestamp()
        cached = self._levels_cache.get(user_id)
        if cached and cached[0] > now:
            return cached[1]
        rows = await self.skills.get_all(user_id)
        self._levels_cache[user_id] = (now + self.cache_ttl, rows)
        return rows

    def invalidate(self, user_id: int) -> None:
        """Skill төлөв өөрчлөгдсөн бүрд дуудна (upgrade/activate/consume/reset)."""
        self._levels_cache.pop(user_id, None)

    def _level(self, rows: dict[str, SkillRow], skill_id: str) -> int:
        row = rows.get(skill_id)
        return row.skill_level if row else 0

    async def get_modifiers(self, user_id: int) -> Modifiers:
        """Бүх сервисийн дуудах гол метод."""
        rows = await self._load_levels(user_id)

        def scaled(skill_id: str) -> float:
            skill = SKILLS[skill_id]
            return min(
                self._level(rows, skill_id) * skill.per_level_value, skill.value_cap
            )

        golden = scaled("golden_touch")
        lucky = scaled("lucky_star")
        merchant = scaled("merchants_eye")
        shadow = scaled("shadow_step")
        resonance = scaled("astral_resonance")

        shadow_lv = self._level(rows, "shadow_step")
        shadow_skill = SKILLS["shadow_step"]
        fine_reduction = min(
            shadow_lv * shadow_skill.secondary_per_level,
            shadow_skill.secondary_cap,
        )
        crit = rows.get("critical_strike")
        shield = rows.get("aether_shield")

        return Modifiers(
            work_income_mult=1.0 + golden,
            casino_cashback_pct=lucky,
            shop_discount_pct=merchant,
            rob_success_bonus=shadow,
            # Баригдвал төлөх торгууль: түвшин бүрт 5%, дээд тал нь 25% бууралт
            rob_fine_mult=1.0 - fine_reduction,
            xp_gain_mult=1.0 + resonance,
            crit_active=_is_active(crit.active_until if crit else None),
            shield_active=_is_active(shield.active_until if shield else None),
        )

    async def get_states(self, user_id: int) -> dict[str, SkillState]:
        rows = await self._load_levels(user_id)
        states: dict[str, SkillState] = {}
        for skill_id, skill in SKILLS.items():
            row = rows.get(skill_id)
            states[skill_id] = SkillState(
                skill=skill,
                level=row.skill_level if row else 0,
                last_used_at=from_db(row.last_used_at) if row else None,
                active_until=from_db(row.active_until) if row else None,
            )
        return states

    async def get_tree(self, user_id: int) -> SkillTree:
        user = await self.users.get(user_id)
        if user is None:
            # Унших зам дээр бичихгүй: мөр үүсгэх шаардлагатай бол л
            # per-user lock + транзакц дор үүсгэнэ.
            async with user_lock(user_id), self.db.transaction():
                user = await self.users.get_or_create(user_id)
        states = await self.get_states(user_id)
        by_path = skills_by_path()
        return SkillTree(
            user_id=user_id,
            skill_points=user.skill_points,
            level=user.level,
            paths={
                path_id: [states[skill.skill_id] for skill in skills]
                for path_id, skills in by_path.items()
            },
        )

    async def get_skill_state(self, user_id: int, skill_id: str) -> SkillState:
        skill = get_skill(skill_id)
        if skill is None:
            raise SkillNotFoundError()
        states = await self.get_states(user_id)
        return states[skill_id]

    # ── Бичих ─────────────────────────────────────────────────────────
    async def upgrade(self, user_id: int, skill_id: str) -> UpgradeResult:
        """SP-ээр skill-ийг 1 түвшин нэмнэ."""
        skill = get_skill(skill_id)
        if skill is None:
            raise SkillNotFoundError()

        async with user_lock(user_id), self.db.transaction():
            user = await self.users.get_or_create(user_id)
            if user.level < skill.unlock_level:
                raise SkillLockedError(
                    f"✦ **{skill.name}**-ийг нээхэд **Lv.{skill.unlock_level}** шаардлагатай "
                    f"(таны түвшин **Lv.{user.level}**)."
                )

            current = await self.skills.get(user_id, skill_id)
            previous_level = current.skill_level if current else 0
            if previous_level >= skill.max_level:
                raise SkillMaxedError(
                    f"✦ **{skill.name}** аль хэдийн дээд түвшин (**Lv.{skill.max_level}**)-дээ хүрсэн."
                )
            if user.skill_points < 1:
                raise InsufficientSkillPointsError(
                    f"✦ **{skill.name}**-ийг сайжруулахад **1 SP** шаардлагатай. "
                    "Түвшин ахиж SP цуглуулна уу."
                )

            if not await self.users.spend_skill_points(user_id, 1):
                raise InsufficientSkillPointsError()

            new_level = await self.skills.increment_level(
                user_id, skill_id, skill.max_level
            )
            if new_level <= previous_level:  # онолын race — SP-г буцаана
                await self.users.grant_skill_points(user_id, 1)
                raise SkillMaxedError()

            sp_left = int(
                await self.db.fetchval(
                    "SELECT skill_points FROM users WHERE user_id = ?", (user_id,), 0
                )
            )

        self.invalidate(user_id)
        result = UpgradeResult(
            skill=skill,
            previous_level=previous_level,
            new_level=new_level,
            skill_points_left=sp_left,
        )
        if self.bus is not None:
            await self.bus.publish(
                SkillUpgraded(
                    user_id=user_id,
                    skill_id=skill_id,
                    previous_level=previous_level,
                    new_level=new_level,
                    skill_points_left=sp_left,
                )
            )
        log.info(
            "Skill upgrade: user=%s %s %s→%s",
            user_id,
            skill_id,
            previous_level,
            new_level,
        )
        return result

    async def activate(self, user_id: int, skill_id: str) -> ActivationResult:
        """Active skill-ийг cooldown шалгаад асаана."""
        skill = get_skill(skill_id)
        if skill is None:
            raise SkillNotFoundError()
        if skill.kind != ACTIVE:
            raise SkillNotActiveTypeError(
                f"✦ **{skill.name}** нь Passive skill — идэвхжүүлэх шаардлагагүй."
            )

        async with user_lock(user_id), self.db.transaction():
            user = await self.users.get_or_create(user_id)
            if user.level < skill.unlock_level:
                raise SkillLockedError(
                    f"✦ **{skill.name}**-ийг нээхэд **Lv.{skill.unlock_level}** шаардлагатай "
                    f"(таны түвшин **Lv.{user.level}**)."
                )

            current = await self.skills.get(user_id, skill_id)
            if not current or current.skill_level < 1:
                raise SkillNotUsableError(
                    f"✦ **{skill.name}**-ийг эхлээд **SP**-ээр нээсэн байх ёстой."
                )

            last_used = from_db(current.last_used_at)
            if last_used is not None and skill.cooldown_sec > 0:
                remaining = skill.cooldown_sec - seconds_since(last_used)
                if remaining > 0:
                    raise CooldownError(skill.name, remaining)

            now = utcnow()
            active_until = now + timedelta(seconds=max(0, skill.duration_sec))
            await self.skills.set_activation(
                user_id,
                skill_id,
                last_used_at=to_db(now),
                active_until=to_db(active_until) if skill.duration_sec else None,
            )

        self.invalidate(user_id)
        result = ActivationResult(
            skill=skill, active_until=active_until, cooldown_sec=skill.cooldown_sec
        )
        if self.bus is not None:
            await self.bus.publish(
                SkillActivated(
                    user_id=user_id,
                    skill_id=skill_id,
                    active_until=active_until,
                    cooldown_sec=skill.cooldown_sec,
                )
            )
        log.info(
            "Skill activated: user=%s %s until=%s", user_id, skill_id, active_until
        )
        return result

    async def consume_charge(self, user_id: int, skill_id: str) -> bool:
        """Нэг удаагийн эффектийг зарцуулна (жишээ: Critical Strike → Duel).

        Идэвхтэй бол `True` буцааж, эффектийг цэвэрлэнэ. Эс бөгөөс `False`.
        """
        skill = get_skill(skill_id)
        if skill is None:
            raise SkillNotFoundError()
        if skill.kind != ACTIVE:
            raise SkillNotActiveTypeError(
                f"✦ **{skill.name}** нь Passive skill — зарцуулах цэнэггүй."
            )

        async with user_lock(user_id), self.db.transaction():
            current = await self.skills.get(user_id, skill_id)
            active_until = from_db(current.active_until) if current else None
            if active_until is None or active_until <= utcnow():
                return False
            await self.skills.clear_active(user_id, skill_id)
        self.invalidate(user_id)
        return True

    async def reset(self, user_id: int) -> ResetResult:
        """Бүх skill-ийг буцааж, зарцуулсан SP-г буцаана.

        ⚠️ Үүнийг зөвхөн `ShopService` (Tome of Rebirth-ийг хэрэглэсний дараа)
        дуудна — шууд дуудахад item шаардлагыг тойрч гарна.
        """
        async with user_lock(user_id), self.db.transaction():
            await self.users.get_or_create(user_id)
            spent = await self.skills.total_spent_points(user_id)
            await self.skills.delete_all(user_id)
            sp = await self.users.grant_skill_points(user_id, spent)

        self.invalidate(user_id)
        log.info("Skill reset: user=%s refunded=%s sp=%s", user_id, spent, sp)
        return ResetResult(refunded_points=spent, skill_points=sp)

    # ── UI-д зориулсан туслах ─────────────────────────────────────────
    async def get_unlock_hint(self, user_id: int, skill_id: str) -> str:
        skill = get_skill(skill_id)
        if skill is None:
            raise SkillNotFoundError()
        state = await self.get_skill_state(user_id, skill_id)
        if not state.is_owned:
            return f"Түгжээтэй · Lv.{skill.unlock_level} шаардлагатай"
        if state.is_active:
            return f"Идэвхтэй · {humanize_seconds(seconds_until(state.active_until))} үлдсэн"
        if state.cooldown_remaining:
            return f"Cooldown · {humanize_seconds(state.cooldown_remaining)}"
        return "Бэлэн"

    def paths(self) -> dict[str, object]:
        """UI SelectMenu-д зориулсан path метадата."""
        return dict(PATHS)
