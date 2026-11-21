"""Skill tree-ийн тодорхойлолт (домайн өгөгдөл).

Энэ файл нь зөвхөн өгөгдөл агуулна — ямар ч логик, DB, discord хамааралгүй.
SkillService үүнийг уншиж modifier тооцоолно; UI үүнээс нэр, тайлбар авна.
"""

from __future__ import annotations

from dataclasses import dataclass

PASSIVE = "passive"
ACTIVE = "active"

FORTUNE = "fortune"
SHADOW = "shadow"
WISDOM = "wisdom"


@dataclass(frozen=True, slots=True)
class PathDef:
    path_id: str
    name: str
    icon: str
    description: str


@dataclass(frozen=True, slots=True)
class SkillDef:
    skill_id: str
    name: str
    path: str
    icon: str
    kind: str  # passive | active
    max_level: int
    description: str
    unlock_level: int = 1
    cooldown_sec: int = 0
    duration_sec: int = 0
    # Эффектийн нэгж утга (жишээ нь: түвшин бүрт +6% → 0.06)
    per_level_value: float = 0.0
    value_cap: float = 0.0
    # Хоёрдогч эффект (жишээ нь: Shadow Step-ийн торгуулийн бууралт)
    secondary_per_level: float = 0.0
    secondary_cap: float = 0.0


PATHS: dict[str, PathDef] = {
    FORTUNE: PathDef(
        FORTUNE,
        "Path of Fortune",
        "💰",
        "Аз, худалдаа, эдийн засгийн зам. Орлогыг өсгөж, эрсдэлийг бууруулна.",
    ),
    SHADOW: PathDef(
        SHADOW,
        "Path of Shadow",
        "🗡️",
        "Эрсдэл ба тулааны зам. Дээрэм, PvP болон шүүмжлэлт довтолгоонд хүчтэй.",
    ),
    WISDOM: PathDef(
        WISDOM,
        "Path of Wisdom",
        "🔮",
        "Хөгжил ба хамгаалалтын зам. XP өсгөж, гадны довтолгооноос хамгаална.",
    ),
}


SKILLS: dict[str, SkillDef] = {
    # ── Path of Fortune ────────────────────────────────────────────────
    "golden_touch": SkillDef(
        skill_id="golden_touch",
        name="Golden Touch",
        path=FORTUNE,
        icon="🪙",
        kind=PASSIVE,
        max_level=5,
        description="/daily болон /work-ийн орлогыг түвшин бүрт **+6%** нэмнэ.",
        unlock_level=1,
        per_level_value=0.06,
        value_cap=0.30,
    ),
    "lucky_star": SkillDef(
        skill_id="lucky_star",
        name="Lucky Star",
        path=FORTUNE,
        icon="⭐",
        kind=PASSIVE,
        max_level=5,
        description="Казинод хожигдсон бооцооны **2%–10%**-ийг буцаан авна (хожих магадлалд нөлөөлөхгүй).",
        unlock_level=3,
        per_level_value=0.02,
        value_cap=0.10,
    ),
    "merchants_eye": SkillDef(
        skill_id="merchants_eye",
        name="Merchant's Eye",
        path=FORTUNE,
        icon="👁️",
        kind=PASSIVE,
        max_level=3,
        description="Дэлгүүрийн үнийг **5%–15%** хямдруулна.",
        unlock_level=5,
        per_level_value=0.05,
        value_cap=0.15,
    ),
    # ── Path of Shadow ─────────────────────────────────────────────────
    "shadow_step": SkillDef(
        skill_id="shadow_step",
        name="Shadow Step",
        path=SHADOW,
        icon="🌑",
        kind=PASSIVE,
        max_level=5,
        description="/rob-ийн амжилтыг түвшин бүрт **+4%** болгож, баригдвал төлөх торгуулийг бууруулна.",
        unlock_level=1,
        per_level_value=0.04,
        value_cap=0.20,
        secondary_per_level=0.05,
        secondary_cap=0.25,
    ),
    "critical_strike": SkillDef(
        skill_id="critical_strike",
        name="Critical Strike",
        path=SHADOW,
        icon="💥",
        kind=ACTIVE,
        max_level=1,
        description="Дараагийн 1 PvP Duel эсвэл Boss Game-ийн хохирол/оноог **1.5x** болгоно.",
        unlock_level=8,
        cooldown_sec=2 * 60 * 60,
        duration_sec=60 * 60,  # цэнэглэгдсэн төлөв 1 цаг хүчинтэй
    ),
    # ── Path of Wisdom ─────────────────────────────────────────────────
    "astral_resonance": SkillDef(
        skill_id="astral_resonance",
        name="Astral Resonance",
        path=WISDOM,
        icon="✨",
        kind=PASSIVE,
        max_level=5,
        description="Бүх үйлдлээс авах XP-г түвшин бүрт **+5%** нэмнэ.",
        unlock_level=1,
        per_level_value=0.05,
        value_cap=0.25,
    ),
    "aether_shield": SkillDef(
        skill_id="aether_shield",
        name="Aether Shield",
        path=WISDOM,
        icon="🛡️",
        kind=ACTIVE,
        max_level=1,
        description="**3 цагийн** турш дээрэмдүүлэхээс 100% хамгаална.",
        unlock_level=6,
        cooldown_sec=6 * 60 * 60,
        duration_sec=3 * 60 * 60,
    ),
}


def get_skill(skill_id: str) -> SkillDef | None:
    return SKILLS.get(skill_id)


def skills_for_path(path_id: str) -> list[SkillDef]:
    return [s for s in SKILLS.values() if s.path == path_id]


def skills_by_path() -> dict[str, list[SkillDef]]:
    return {path_id: skills_for_path(path_id) for path_id in PATHS}
