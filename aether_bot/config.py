"""Aether-ийн төвлөрсөн тохиргоо: env, өнгөний палитр, тоглоомын тогтмолууд.

UI давхарга болон service давхарга хоёулаа зөвхөн энэ файлаас тогтмол уншина.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

try:  # python-dotenv заавал биш (Docker/CI дээр env шууд ирж болно)
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

BASE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = BASE_DIR / "migrations"


class ConfigError(RuntimeError):
    """Тохиргооны утга буруу — бот ажиллахаас өмнө тодорхой мессежтэй унана."""


@dataclass(frozen=True, slots=True)
class Settings:
    discord_token: str
    guild_id: int
    db_path: Path
    rate_limit_per_second: int
    log_level: str
    default_prefix: str


def _read_int(
    source: Mapping[str, str],
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw = (source.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} бүхэл тоо байх ёстой, одоо: {raw!r}") from exc
    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} >= {minimum} байх ёстой, одоо: {value}")
    if maximum is not None and value > maximum:
        value = maximum
    return value


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Env-ээс тохиргоог цэвэр функцээр уншина (тестлэхэд хялбар)."""
    source = os.environ if env is None else env

    raw_db = (source.get("AETHER_DB_PATH") or "").strip()
    db_path = Path(raw_db).expanduser() if raw_db else BASE_DIR / "data" / "aether.db"
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    guild_id = _read_int(source, "GUILD_ID", 0, minimum=0)
    # Discord-ийн 50 req/s хязгаараас доогуур аюулгүй босго.
    rate_limit = _read_int(source, "RATE_LIMIT_PER_SECOND", 45, minimum=1)
    rate_limit = min(rate_limit, 45)

    log_level = (source.get("LOG_LEVEL") or "INFO").strip().upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfigError(
            "LOG_LEVEL нь DEBUG/INFO/WARNING/ERROR/CRITICAL-ийн нэг байх ёстой, "
            f"одоо: {log_level!r}"
        )

    prefix = (source.get("DEFAULT_PREFIX") or "a!").strip()
    if not 1 <= len(prefix) <= 5:
        raise ConfigError("DEFAULT_PREFIX 1–5 тэмдэгт байх ёстой.")

    return Settings(
        discord_token=(source.get("DISCORD_TOKEN") or "").strip(),
        guild_id=guild_id,
        db_path=db_path,
        rate_limit_per_second=rate_limit,
        log_level=log_level,
        default_prefix=prefix,
    )


SETTINGS = load_settings()

# ── Runtime ────────────────────────────────────────────────────────────────
DISCORD_TOKEN = SETTINGS.discord_token
GUILD_ID = SETTINGS.guild_id
DB_PATH = SETTINGS.db_path
LOG_LEVEL = SETTINGS.log_level
DEFAULT_PREFIX = SETTINGS.default_prefix

# Discord-ийн 50 req/s хязгаараас доогуур аюулгүй босго
RATE_LIMIT_PER_SECOND = SETTINGS.rate_limit_per_second


def require_token() -> str:
    """Bot.run()-ийн өмнө тодорхой алдаа өгнө."""
    if not DISCORD_TOKEN:
        raise ConfigError(
            "DISCORD_TOKEN тохируулаагүй байна. .env файл эсвэл орчны "
            "хувьсагчаар Discord bot token өгнө үү."
        )
    return DISCORD_TOKEN


# ── Өнгөний систем (Anime / Cyber-Fantasy) ─────────────────────────────────
PRIMARY = 0x8A2BE2  # Aether Violet — ерөнхий, профайл
CYAN = 0x00E5FF  # Cyan Glow — мэдээлэл, skill tree
SUCCESS = 0x2ECC71  # Emerald — амжилт, хожил
DANGER = 0xFF4757  # Crimson — алдаа, хожигдол
GOLD = 0xFFD700  # Astral Gold — домогт, jackpot
MUTED = 0x5865F2  # төвийг сахисан

# ── Визуал тогтмолууд ──────────────────────────────────────────────────────
BRAND_AUTHOR = "✦ AETHER SYSTEM ✦"
SEPARATOR = "──────────"

FOOTER_QUOTES = (
    "✦ Aether System • Оддын зам таныг дуудна",
    "✦ Aether System • Сүүдрийн дунд ч гэрэл байна",
    "✦ Aether System • Азаа өөрөө бүтээ",
    "✦ Aether System • Хүч бол хүлээцтэй байдал",
)

# ── Эдийн засгийн тэнцвэр ─────────────────────────────────────────────────
STARTING_WALLET = 500
DAILY_BASE_REWARD = 250
DAILY_LEVEL_BONUS = 50  # level бүрээс нэмэгдэх дүн
DAILY_STREAK_BONUS_PCT = 0.05  # streak хоног бүрт +5% (max 50%)
DAILY_STREAK_MAX_PCT = 0.50
DAILY_COOLDOWN_SEC = 24 * 60 * 60
DAILY_XP = 40

WORK_COOLDOWN_SEC = 30 * 60
ROB_COOLDOWN_SEC = 60 * 60
ROB_BASE_SUCCESS = 0.35
ROB_FINE_PCT = 0.15  # баригдвал Wallet-ийн 15% торгууль
ROB_MAX_STEAL_PCT = 0.30  # зорилтын Wallet-ийн хамгийн ихдээ 30%

TRANSFER_MIN = 1
TRANSFER_MAX = 10_000_000
DEPOSIT_MIN = 1
WITHDRAW_MIN = 1

# ── Crime & Jail ──────────────────────────────────────────────────────────
CRIME_COOLDOWN_SEC = 45 * 60
CRIME_FAIL_JAIL_MINUTES = 8
CRIME_FAIL_BAIL = 600
ROB_JAIL_MINUTES = 10
ROB_JAIL_BAIL = 800
JAIL_MAX_MINUTES = 24 * 60

CASINO_HOUSE_EDGE = 0.04  # 4% — инфляцийн хамгаалалт
CASINO_MIN_BET = 50
CASINO_MAX_BET = 250_000
LOTTERY_TICKET_PRICE = 250
LOTTERY_MAX_TICKETS_PER_ROUND = 20

# ── Games ─────────────────────────────────────────────────────────────────
DUEL_MIN_BET = 50
DUEL_MAX_BET = 100_000
ADVENTURE_COOLDOWN_SEC = 20 * 60
HUNT_COOLDOWN_SEC = 15 * 60
FISH_COOLDOWN_SEC = 15 * 60
BOSS_COOLDOWN_SEC = 30 * 60

# ── Түвшин ба XP ──────────────────────────────────────────────────────────
XP_PER_MESSAGE = 8
XP_MESSAGE_COOLDOWN_SEC = 60
LEVEL_SKILL_POINTS = 2
LEVEL_COIN_REWARD_MULT = 200  # level * 200
MAX_LEVEL = 100
