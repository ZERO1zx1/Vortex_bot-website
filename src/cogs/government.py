"""Government Economy System cog for Aether.

Four slash commands drive the whole system behind rich UI (buttons, select
menus, modals, confirmations, pagination):

  /government         guild officials, government roles, co-owners, toggle
  /economy-config     tax config, recipients, custom jobs, role income
  /treasury           treasury balance, payments, history, distribution
  /economy            user-facing panel (balance, jobs, tax info, government)

Permission hierarchy (re-validated at runtime on every button/select/modal
callback — never trusted from client-side state):
  1. Discord Guild Owner (always, never locked out)
  2. Co-Owners (per-guild user IDs; only the owner appoints/removes)
  3. Government Admin role (government_admin) / President
  4. Finance role (economy + treasury management)
  5. Tax Collector role (read-only treasury access)

All government roles are stored as ROLE IDs (never names). Unconfigured guilds
keep the legacy economy behavior exactly as before: the legacy tax rate and
collector-role distribution remain active until ``/government`` is enabled.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord import SelectOption
from discord import app_commands
from discord.ui import Button, Modal, RoleSelect, Select, TextInput, UserSelect, View

from src.utils.constants import ERROR_COLOR, GOLD_COLOR, INFO_COLOR, SUCCESS_COLOR, WARNING_COLOR
from src.utils.embed_style import add_box_field
from src.utils.supabase_cog import SupabaseCog

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Settings / constants
# ---------------------------------------------------------------------------
SETTINGS_TABLE = "economy_guild_settings"
MEMBERS_TABLE = "government_members"
ROLES_TABLE = "government_roles"
JOBS_TABLE = "economy_jobs"
RECIPIENTS_TABLE = "tax_recipients"
LEDGER_TABLE = "economy_ledger"
ROLE_INCOME_TABLE = "role_income"

DEFAULT_TAX_RATE = 10
MAX_JOB_NAME_LEN = 40
MAX_SALARY = 1_000_000
MAX_TREASURY_PAY_RECIPIENTS = 50
MAX_TREASURY_PAY_AMOUNT = 100_000_000_000
MIN_ROLE_INCOME_AMOUNT = 1
MAX_ROLE_INCOME_AMOUNT = 1_000_000
MIN_ROLE_INCOME_INTERVAL = 3600            # 1 hour — prevents payout spam
MAX_ROLE_INCOME_INTERVAL = 7 * 24 * 3600   # 1 week

JOBS_PER_PAGE = 5
LEDGER_PER_PAGE = 10

# role_type -> (label, hierarchy_level)
ROLE_TYPE_LABELS = {
    "government_admin": ("🏛️ Засгийн газрын админ", 3),
    "president": ("👑 Ерөнхийлөгч", 3),
    "finance": ("💰 Сангийн сайд", 4),
    "tax_collector": ("🧾 Татвар цуглуулагч", 5),
}
ROLE_TYPE_ORDER = ("government_admin", "president", "finance", "tax_collector")

RECIPIENT_TYPE_LABELS = {
    "treasury": "🏛️ Тэтгэвэр",
    "owner": "👑 Сервер эзэмшигч",
    "co_owner": "👥 Co-owner",
    "user": "🧑 Хэрэглэгч",
    "role": "🎭 Role",
}

TXN_ICONS = {
    "tax_collected": "🧾",
    "tax_distributed": "📤",
    "treasury_payment": "💸",
    "treasury_payout": "👤",
    "treasury_deposit": "🏦",
    "job_salary": "💼",
    "role_income": "💰",
    "admin_adjustment": "🛠️",
}


def _fmt_money(n: int) -> str:
    n = max(0, int(n or 0))
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B ₮"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M ₮"
    return f"{n:,} ₮"


def _role_mention(role_id) -> str:
    return f"<@&{role_id}>"


def fmt_interval(seconds: int) -> str:
    seconds = int(seconds or 0)
    days, rem = divmod(seconds, 86400)
    hours, _rem = divmod(rem, 3600)
    if days and hours:
        return f"{days}хоног {hours}ц"
    if days:
        return f"{days}хоног"
    return f"{hours}ц"


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested)
# ---------------------------------------------------------------------------
def _parse_int(text: str) -> Optional[int]:
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return None


def parse_pct(text: str) -> Optional[int]:
    v = _parse_int(text)
    if v is None or v < 0 or v > 100:
        return None
    return v


def parse_money(text: str, maximum: int = MAX_SALARY) -> Optional[int]:
    v = _parse_int(text)
    if v is None or v < 0 or v > maximum:
        return None
    return v


def parse_level(text: str) -> Optional[int]:
    v = _parse_int(text)
    if v is None or v < 0:
        return None
    return v


def parse_role_ref(text: str) -> Optional[int]:
    """Accept '123', '<@&123>'; '0', '-', '' mean "clear" (-> None)."""
    raw = str(text or "").strip()
    if raw in ("", "-", "0", "—"):
        return None
    if raw.startswith("<@&") and raw.endswith(">"):
        raw = raw[3:-1]
    return _parse_int(raw)


def compute_tax(gross: int, rate_pct: int) -> Tuple[int, int]:
    """Return (tax, net). tax is floored; rate clamped to [0, 100]."""
    rate = max(0, min(100, int(rate_pct or 0)))
    if gross <= 0 or rate <= 0:
        return 0, gross
    tax = gross * rate // 100
    return tax, gross - tax


def allocate_dividend(total: int, parts: int) -> List[int]:
    """Equal integer split; rounding remainder goes to the first part."""
    if parts <= 0:
        return []
    if total <= 0:
        return [0] * parts
    share, rem = divmod(int(total), parts)
    return [share + rem] + [share] * (parts - 1)


def recipient_total(recipients: List[Dict[str, Any]]) -> int:
    return sum(int(r.get("percentage") or 0) for r in recipients)


def validate_recipient_set(recipients: List[Dict[str, Any]]) -> Tuple[bool, int, str]:
    """recipients must sum to exactly 100 to be active (never more)."""
    total = recipient_total(recipients)
    if total > 100:
        return False, total, "Хуваарилалтын нийт хувь 100%-аас хэтэрсэн байна."
    if total < 100:
        return False, total, (
            f"Нийт хувь {total}% байна. 100% болтол хуваарилалт идэвхжихгүй "
            "(татвар Тэтгэвэрт орно)."
        )
    return True, total, "✅ Хуваарилалт идэвхтэй."


def validate_job_fields(
    name: str,
    emoji: str,
    level: int,
    salary_min: int,
    salary_max: int,
    existing_names: List[str],
    role_id: Optional[int] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    name = (name or "").strip()
    if not name:
        return False, "Ажлын нэр хоосон байж болохгүй.", None
    if len(name) > MAX_JOB_NAME_LEN:
        return False, f"Ажлын нэр хамгийн ихдээ {MAX_JOB_NAME_LEN} тэмдэгт байна.", None
    for existing in existing_names:
        if existing and existing.strip().casefold() == name.casefold():
            return False, f"`{name}` нэртэй ажил аль хэдийн байна.", None
    emoji = (emoji or "💼").strip()[:8] or "💼"
    if level is None or level < 0:
        return False, "Шаардлагатай түвшин сөрөг байж болохгүй.", None
    if salary_min is None or salary_min < 0:
        return False, "Хамгийн бага цалин сөрөг байж болохгүй.", None
    if salary_max is None or salary_max < salary_min:
        return False, "Хамгийн их цалин нь хамгийн багацаас бага байж болохгүй.", None
    if salary_max > MAX_SALARY:
        return False, f"Цалин хамгийн ихдээ {MAX_SALARY:,} ₮ байна.", None
    return True, "ok", {
        "name": name,
        "emoji": emoji,
        "required_level": int(level or 0),
        "salary_min": int(salary_min),
        "salary_max": int(salary_max),
        "required_role_id": role_id,
    }


def validate_role_income(amount: int, interval_seconds: int) -> Tuple[bool, str, Optional[Tuple[int, int]]]:
    if amount is None or amount < MIN_ROLE_INCOME_AMOUNT or amount > MAX_ROLE_INCOME_AMOUNT:
        return False, f"Дүн {MIN_ROLE_INCOME_AMOUNT:,}-{MAX_ROLE_INCOME_AMOUNT:,} ₮ хооронд байна.", None
    if interval_seconds is None or interval_seconds < MIN_ROLE_INCOME_INTERVAL:
        return False, (
            f"Интервал {MIN_ROLE_INCOME_INTERVAL // 3600} цагаас бага байж болохгүй "
            "(spam сэргийлэх)."
        ), None
    if interval_seconds > MAX_ROLE_INCOME_INTERVAL:
        return False, "Интервал дээд тал нь 7 хоног байна.", None
    return True, "ok", (int(amount), int(interval_seconds))


def build_distribution_plan(
    guild: Any,
    recipients: List[Dict[str, Any]],
    co_owner_ids: List[int],
    tax: int,
) -> Dict[str, Any]:
    """Turn configured recipients + a tax amount into concrete credits.

    Rules:
      * owner comes from the live guild owner (never a stored user row)
      * role/user recipients missing a guild member fall back to treasury
      * co-owner/role shares split equally; remainder is deterministic
      * a user appearing twice is credited once (no double pay); the second
        share returns to the treasury instead
      * integer rounding loss always returns to the treasury (no minting)
    """
    credits: List[Tuple[int, int, str]] = []
    treasury = 0
    credited_uids = set()

    tax = int(tax or 0)
    if tax <= 0:
        return {"credits": [], "treasury": 0, "tax": 0}

    def add_user(uid, amount: int) -> None:
        nonlocal treasury
        if amount <= 0:
            return
        if uid is None or int(uid) in credited_uids:
            treasury += amount
            return
        credited_uids.add(int(uid))
        credits.append((int(uid), amount, ""))

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in recipients:
        grouped.setdefault(r.get("recipient_type") or "", []).append(r)

    for r in grouped.get("treasury", []):
        treasury += int(tax * int(r.get("percentage") or 0) // 100)

    for r in grouped.get("owner", []):
        amount = int(tax * int(r.get("percentage") or 0) // 100)
        add_user(getattr(guild, "owner_id", None), amount)

    for r in grouped.get("co_owner", []):
        amount = int(tax * int(r.get("percentage") or 0) // 100)
        ids = [u for u in co_owner_ids]
        if not ids:
            treasury += amount
            continue
        splits = allocate_dividend(amount, len(ids))
        for uid, amt in zip(ids, splits):
            add_user(uid, amt)

    for r in grouped.get("role", []):
        amount = int(tax * int(r.get("percentage") or 0) // 100)
        role = guild.get_role(int(r.get("recipient_key") or 0)) if guild else None
        members = []
        if role is not None:
            members = [m for m in getattr(role, "members", []) if not getattr(m, "bot", False)]
        if role is None or not members:
            treasury += amount
            continue
        splits = allocate_dividend(amount, len(members))
        for m, amt in zip(members, splits):
            add_user(m.id, amt)

    for r in grouped.get("user", []):
        amount = int(tax * int(r.get("percentage") or 0) // 100)
        uid = int(r.get("recipient_key") or 0)
        member = guild.get_member(uid) if guild else None
        if member is None:
            treasury += amount
            continue
        add_user(uid, amount)

    rounding = tax - sum(c[1] for c in credits) - treasury
    if rounding > 0:
        treasury += rounding

    return {"credits": credits, "treasury": treasury, "tax": tax}


# ---------------------------------------------------------------------------
# Permission bag
# ---------------------------------------------------------------------------
class GovPerms:
    __slots__ = ("owner", "co_owner", "government", "economy", "treasury_ro", "treasury_manage")

    def __init__(self):
        self.owner = False
        self.co_owner = False
        self.government = False       # owner / co-owner / government_admin / president
        self.economy = False          # above + finance
        self.treasury_ro = False      # can view treasury info (tax collector+)
        self.treasury_manage = False  # can run treasury payments / history


# ---------------------------------------------------------------------------
# The cog
# ---------------------------------------------------------------------------
class Government(SupabaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot
        self._treasury_locks: Dict[str, asyncio.Lock] = {}
        self._tax_locks: Dict[str, asyncio.Lock] = {}
        self._config_locks: Dict[str, asyncio.Lock] = {}
        self._settings_cache: Dict[str, Tuple[float, Optional[Dict[str, Any]]]] = {}
        self._settings_ttl = 15.0

    # ------------------------------------------------------------------
    # infra
    # ------------------------------------------------------------------
    async def _get_lock(self, pool: Dict[str, asyncio.Lock], key: str) -> asyncio.Lock:
        lock = pool.get(key)
        if lock is None:
            lock = asyncio.Lock()
            pool[key] = lock
        return lock

    async def _upsert_unique(self, table: str, filters: Dict[str, Any], data: Dict[str, Any]):
        row = await self.bot.db_manager.fetch_one(table, filters)
        if row:
            await self.bot.db_manager.update(table, filters, data)
        else:
            await self.bot.db_manager.insert(table, data)

    def _invalidate_economy_tax(self, gid: str):
        eco = self.bot.get_cog("Economy")
        if eco is not None and hasattr(eco, "invalidate_tax_cache"):
            try:
                eco.invalidate_tax_cache(gid)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # guild settings
    # ------------------------------------------------------------------
    async def get_settings(self, guild_id) -> Dict[str, Any]:
        gid = str(guild_id)
        now = time.monotonic()
        cached = self._settings_cache.get(gid)
        if cached and now - cached[0] < self._settings_ttl:
            return dict(cached[1])
        row = await self.bot.db_manager.fetch_one(SETTINGS_TABLE, {"guild_id": gid})
        defaults = {
            "guild_id": gid,
            "government_enabled": False,
            "tax_enabled": True,
            "tax_rate": DEFAULT_TAX_RATE,
            "treasury_balance": 0,
            "treasury_public": False,
        }
        if row:
            for k in list(defaults):
                if k in row:
                    defaults[k] = row[k]
        self._settings_cache[gid] = (now, dict(defaults))
        return defaults

    async def _save_settings(self, guild_id, **kw) -> Dict[str, Any]:
        gid = str(guild_id)
        settings = await self.get_settings(gid)
        settings.update(kw)
        settings["guild_id"] = gid
        settings["updated_at"] = int(time.time())
        await self.bot.db_manager.upsert(SETTINGS_TABLE, settings, on_conflict="guild_id")
        self._settings_cache[gid] = (time.monotonic(), dict(settings))
        self._invalidate_economy_tax(gid)
        return settings

    # ------------------------------------------------------------------
    # government status / tax
    # ------------------------------------------------------------------
    async def is_government_active(self, guild_id) -> bool:
        settings = await self.get_settings(guild_id)
        return bool(settings.get("government_enabled"))

    async def government_tax(self, guild_id) -> Optional[Tuple[int, bool]]:
        """None when the government is inactive (economy keeps legacy rate);
        otherwise (tax_rate, tax_enabled)."""
        settings = await self.get_settings(guild_id)
        if not settings.get("government_enabled"):
            return None
        try:
            rate = max(0, min(100, int(settings.get("tax_rate") or 0)))
        except (TypeError, ValueError):
            rate = DEFAULT_TAX_RATE
        return rate, bool(settings.get("tax_enabled"))

    # ------------------------------------------------------------------
    # government roles (stored by ROLE ID)
    # ------------------------------------------------------------------
    async def get_government_roles(self, guild_id) -> Dict[str, int]:
        rows = await self.bot.db_manager.fetch_safe(
            ROLES_TABLE, {"guild_id": str(guild_id)}, selects="role_type,role_id"
        )
        out = {}
        for r in rows or []:
            try:
                out[r["role_type"]] = int(r["role_id"])
            except (KeyError, TypeError, ValueError):
                continue
        return out

    async def get_government_role(self, guild_id, role_type) -> Optional[int]:
        roles = await self.get_government_roles(guild_id)
        return roles.get(role_type)

    async def set_government_role(self, guild_id, role_type, role_id, updated_by) -> None:
        await self._upsert_unique(
            ROLES_TABLE,
            {"guild_id": str(guild_id), "role_type": role_type},
            {
                "guild_id": str(guild_id),
                "role_type": role_type,
                "role_id": int(role_id),
                "updated_by": str(updated_by),
                "updated_at": int(time.time()),
            },
        )

    async def clear_government_role(self, guild_id, role_type) -> None:
        await self.bot.db_manager.delete(
            ROLES_TABLE, {"guild_id": str(guild_id), "role_type": role_type}
        )

    # ------------------------------------------------------------------
    # co-owners (per-guild, appointed by the guild owner only)
    # ------------------------------------------------------------------
    async def get_co_owner_ids(self, guild_id) -> List[int]:
        rows = await self.bot.db_manager.fetch_safe(
            MEMBERS_TABLE,
            {"guild_id": str(guild_id), "position": "co_owner"},
            selects="user_id",
        )
        ids = []
        for r in rows or []:
            try:
                ids.append(int(r["user_id"]))
            except (KeyError, TypeError, ValueError):
                continue
        return ids

    async def is_co_owner_id(self, guild_id, user_id) -> bool:
        return int(user_id) in await self.get_co_owner_ids(str(guild_id))

    async def add_co_owner(self, guild_id, user_id, appointed_by) -> Tuple[bool, str]:
        gid = str(guild_id)
        uid = str(user_id)
        if await self.is_co_owner_id(gid, uid):
            return False, "Энэ хэрэглэгч аль хэдийн co-owner байна."
        await self.bot.db_manager.insert(
            MEMBERS_TABLE,
            {
                "guild_id": gid,
                "user_id": uid,
                "position": "co_owner",
                "appointed_by": str(appointed_by),
                "created_at": int(time.time()),
            },
        )
        return True, "✅ Co-owner нэмэгдлээ."

    async def remove_co_owner(self, guild_id, user_id) -> Tuple[bool, str]:
        gid = str(guild_id)
        uid = str(user_id)
        if not await self.is_co_owner_id(gid, uid):
            return False, "Энэ хэрэглэгч co-owner биш байна."
        await self.bot.db_manager.delete(
            MEMBERS_TABLE, {"guild_id": gid, "user_id": uid, "position": "co_owner"}
        )
        return True, "✅ Co-owner хасагдлаа."

    # ------------------------------------------------------------------
    # tax recipients
    # ------------------------------------------------------------------
    async def get_recipients(self, guild_id) -> List[Dict[str, Any]]:
        rows = await self.bot.db_manager.fetch_safe(
            RECIPIENTS_TABLE, {"guild_id": str(guild_id)}
        )
        out = []
        for r in rows or []:
            out.append({
                "id": r.get("id"),
                "guild_id": r.get("guild_id"),
                "recipient_type": r.get("recipient_type"),
                "recipient_key": int(r.get("recipient_key") or 0),
                "percentage": int(r.get("percentage") or 0),
                "created_by": r.get("created_by"),
            })
        return out

    async def set_recipient(self, guild_id, recipient_type, recipient_key, pct, created_by) -> Tuple[bool, str]:
        gid = str(guild_id)
        if recipient_type not in RECIPIENT_TYPE_LABELS:
            return False, "Буруу хүлээн авагчийн төрөл."
        pct = int(pct or 0)
        if pct < 0 or pct > 100:
            return False, "Хувь 0-100 хооронд байх ёстой."
        key = int(recipient_key or 0)
        if recipient_type in ("user", "role") and key <= 0:
            return False, "Хүлээн авагчийг сонгоно уу."
        if pct == 0:
            await self.remove_recipient(gid, recipient_type, key)
            return True, "🗑️ 0% учраас хүлээн авагч хасагдлаа."
        async with await self._get_lock(self._config_locks, f"recip:{gid}"):
            recipients = await self.get_recipients(gid)
            if recipient_type in ("treasury", "owner", "co_owner"):
                # only one row per non-ID type: replace any existing one
                await self.bot.db_manager.delete(
                    RECIPIENTS_TABLE, {"guild_id": gid, "recipient_type": recipient_type}
                )
                key = 0
            total_except = recipient_total([
                r for r in recipients
                if not (r["recipient_type"] == recipient_type and r["recipient_key"] == key)
            ])
            if total_except + pct > 100:
                return False, f"Нийт хувь 100%-аас хэтрэхгүй. Одоо {total_except}% (дээд тал нь {100 - total_except}%)."
            await self._upsert_unique(
                RECIPIENTS_TABLE,
                {"guild_id": gid, "recipient_type": recipient_type, "recipient_key": key},
                {
                    "guild_id": gid,
                    "recipient_type": recipient_type,
                    "recipient_key": key,
                    "percentage": pct,
                    "created_by": str(created_by),
                    "updated_at": int(time.time()),
                },
            )
            new_total = total_except + pct
            if new_total == 100:
                return True, "✅ Хуваарилалт 100% — идэвхэллээ."
            return True, f"⚠️ Нийт хувь {new_total}% — 100% болтол Тэтгэвэрт очно."
        return False, "Хадгалахад алдаа гарлаа."

    async def remove_recipient(self, guild_id, recipient_type, recipient_key) -> None:
        await self.bot.db_manager.delete(
            RECIPIENTS_TABLE,
            {"guild_id": str(guild_id), "recipient_type": recipient_type, "recipient_key": int(recipient_key or 0)},
        )

    async def clear_recipients(self, guild_id) -> None:
        await self.bot.db_manager.delete(RECIPIENTS_TABLE, {"guild_id": str(guild_id)})

    def recipient_ref(self, guild, recipient: Dict[str, Any]) -> str:
        rtype = recipient.get("recipient_type")
        key = int(recipient.get("recipient_key") or 0)
        if rtype == "user":
            return f"<@{key}>"
        if rtype == "role":
            return _role_mention(key)
        if rtype == "owner":
            return f"<@{getattr(guild, 'owner_id', 0)}>"
        return ""

    # ------------------------------------------------------------------
    # custom jobs
    # ------------------------------------------------------------------
    async def get_custom_jobs(self, guild_id, enabled_only: bool = False) -> List[Dict[str, Any]]:
        rows = await self.bot.db_manager.fetch_safe(
            JOBS_TABLE,
            {"guild_id": str(guild_id)},
            order_by="required_level",
            desc=True,
        )
        jobs = []
        for r in rows or []:
            try:
                job = {
                    "id": r.get("id"),
                    "guild_id": r.get("guild_id"),
                    "name": r.get("name"),
                    "emoji": r.get("emoji") or "💼",
                    "required_level": int(r.get("required_level") or 0),
                    "required_role_id": int(r["required_role_id"]) if r.get("required_role_id") else None,
                    "salary_min": int(r.get("salary_min") or 0),
                    "salary_max": int(r.get("salary_max") or 0),
                    "enabled": bool(r.get("enabled", True)),
                    "created_by": r.get("created_by"),
                }
            except (KeyError, TypeError, ValueError):
                continue
            if enabled_only and not job["enabled"]:
                continue
            jobs.append(job)
        return jobs

    async def get_job(self, guild_id, job_id) -> Optional[Dict[str, Any]]:
        for j in await self.get_custom_jobs(guild_id):
            if str(j.get("id")) == str(job_id):
                return j
        return None

    async def create_job(self, guild_id, payload: Dict[str, Any], created_by) -> Tuple[bool, str]:
        gid = str(guild_id)
        async with await self._get_lock(self._config_locks, f"jobs:{gid}"):
            existing = [j["name"] for j in await self.get_custom_jobs(gid)]
            ok, err, clean = validate_job_fields(
                payload.get("name", ""),
                payload.get("emoji", "💼"),
                payload.get("required_level", 0),
                payload.get("salary_min", 0),
                payload.get("salary_max", 0),
                existing,
                payload.get("required_role_id"),
            )
            if not ok:
                return False, err
            now = int(time.time())
            await self.bot.db_manager.insert(
                JOBS_TABLE,
                {
                    "guild_id": gid,
                    "name": clean["name"],
                    "emoji": clean["emoji"],
                    "required_level": clean["required_level"],
                    "required_role_id": clean["required_role_id"],
                    "salary_min": clean["salary_min"],
                    "salary_max": clean["salary_max"],
                    "enabled": True,
                    "created_by": str(created_by),
                    "created_at": now,
                    "updated_at": now,
                },
            )
        return True, f"✅ `{clean['name']}` ажил нэмэгдлээ."

    async def update_job(self, guild_id, job_id, **fields) -> Tuple[bool, str]:
        gid = str(guild_id)
        job = await self.get_job(gid, job_id)
        if job is None:
            return False, "Ажил олдсонгүй."
        name = fields.get("name", job["name"])
        emoji = fields.get("emoji", job["emoji"])
        level = fields.get("required_level", job["required_level"])
        salary_min = fields.get("salary_min", job["salary_min"])
        salary_max = fields.get("salary_max", job["salary_max"])
        if "required_role_id" in fields:
            role_id = fields["required_role_id"]
        else:
            role_id = job.get("required_role_id")
        others = [
            j["name"] for j in await self.get_custom_jobs(gid)
            if str(j.get("id")) != str(job_id)
        ]
        ok, err, clean = validate_job_fields(
            name, emoji, level, salary_min, salary_max, others, role_id
        )
        if not ok:
            return False, err
        async with await self._get_lock(self._config_locks, f"jobs:{gid}"):
            await self.bot.db_manager.update(
                JOBS_TABLE,
                {"guild_id": gid, "id": job_id},
                {
                    "name": clean["name"],
                    "emoji": clean["emoji"],
                    "required_level": clean["required_level"],
                    "required_role_id": clean["required_role_id"],
                    "salary_min": clean["salary_min"],
                    "salary_max": clean["salary_max"],
                    "updated_at": int(time.time()),
                },
            )
        return True, f"✅ `{clean['name']}` ажил шинэчлэгдлээ."

    async def toggle_job_enabled(self, guild_id, job_id) -> Tuple[bool, str]:
        job = await self.get_job(guild_id, job_id)
        if job is None:
            return False, "Ажил олдсонгүй."
        await self.bot.db_manager.update(
            JOBS_TABLE,
            {"guild_id": str(guild_id), "id": job_id},
            {"enabled": not job["enabled"], "updated_at": int(time.time())},
        )
        state = "асаагдлаа" if not job["enabled"] else "унтраагдлаа"
        return True, f"✅ `{job['name']}` ажил {state}."

    async def delete_job(self, guild_id, job_id) -> Tuple[bool, str]:
        job = await self.get_job(guild_id, job_id)
        if job is None:
            return False, "Ажил олдсонгүй."
        await self.bot.db_manager.delete(JOBS_TABLE, {"guild_id": str(guild_id), "id": job_id})
        return True, f"🗑️ `{job['name']}` ажил устгагдлаа."

    async def resolve_user_job(self, guild_id, level, member=None) -> Optional[Dict[str, Any]]:
        """Best custom job the user qualifies for, or None -> JOB_LEVELS fallback."""
        jobs = await self.get_custom_jobs(guild_id, enabled_only=True)
        eligible = []
        for j in jobs:
            if j["required_level"] > (level or 0):
                continue
            if j.get("required_role_id"):
                if member is None or not any(
                    getattr(r, "id", None) == j["required_role_id"] for r in getattr(member, "roles", ())
                ):
                    continue
            eligible.append(j)
        if not eligible:
            return None
        eligible.sort(key=lambda j: (j["required_level"], j["salary_max"]), reverse=True)
        best = eligible[0]
        return {
            "id": best["id"],
            "name": best["name"],
            "emoji": best["emoji"],
            "min": best["salary_min"],
            "max": best["salary_max"],
            "required_level": best["required_level"],
            "required_role_id": best.get("required_role_id"),
            "custom": True,
        }

    # ------------------------------------------------------------------
    # role income
    # ------------------------------------------------------------------
    async def get_role_incomes(self, guild_id) -> List[Dict[str, Any]]:
        rows = await self.bot.db_manager.fetch_safe(
            ROLE_INCOME_TABLE, {"guild_id": str(guild_id)}
        )
        out = []
        for r in rows or []:
            try:
                out.append({
                    "guild_id": r.get("guild_id"),
                    "role_id": int(r["role_id"]),
                    "amount": int(r.get("amount") or 0),
                    "interval_seconds": int(r.get("interval_seconds") or 3600),
                })
            except (KeyError, TypeError, ValueError):
                continue
        return out

    def get_role_income(self, incomes: List[Dict[str, Any]], role_id) -> Optional[Dict[str, Any]]:
        for inc in incomes:
            if int(inc.get("role_id") or 0) == int(role_id):
                return inc
        return None

    async def set_role_income(self, guild_id, role_id, amount, interval_seconds, changed_by) -> Tuple[bool, str]:
        ok, err, clean = validate_role_income(amount, interval_seconds)
        if not ok:
            return False, err
        amount, interval = clean
        gid = str(guild_id)
        await self._upsert_unique(
            ROLE_INCOME_TABLE,
            {"guild_id": gid, "role_id": int(role_id)},
            {
                "guild_id": gid,
                "role_id": int(role_id),
                "amount": amount,
                "interval_seconds": interval,
            },
        )
        _ = changed_by
        return True, f"✅ Ролын орлого {_fmt_money(amount)} / {fmt_interval(interval)} боллоо."

    async def remove_role_income(self, guild_id, role_id) -> Tuple[bool, str]:
        await self.bot.db_manager.delete(
            ROLE_INCOME_TABLE, {"guild_id": str(guild_id), "role_id": int(role_id)}
        )
        return True, "✅ Ролын орлого хасагдлаа."

    # ------------------------------------------------------------------
    # treasury
    # ------------------------------------------------------------------
    async def get_treasury_balance(self, guild_id) -> int:
        settings = await self.get_settings(guild_id)
        return max(0, int(settings.get("treasury_balance") or 0))

    async def _set_treasury(self, guild_id, value: int) -> None:
        await self._save_settings(guild_id, treasury_balance=max(0, int(value)))

    async def credit_treasury(self, guild_id, amount: int, reason: str) -> bool:
        if amount is None or int(amount) <= 0:
            return False
        gid = str(guild_id)
        async with await self._get_lock(self._treasury_locks, gid):
            before = await self.get_treasury_balance(gid)
            after = before + int(amount)
            await self._set_treasury(gid, after)
            await self.add_ledger(
                guild_id=gid, transaction_type="treasury_deposit", amount=int(amount),
                treasury_before=before, treasury_after=after, reason=reason,
            )
        return True

    async def treasury_pay(self, guild_id, member_ids, amount: int, reason: str, actor_id) -> Tuple[bool, str]:
        gid = str(guild_id)
        amount = int(amount or 0)
        if amount <= 0:
            return False, "Дүн эерэг бүхэл тоо байх ёстой."
        if not member_ids:
            return False, "Хүлээн авагч байхгүй байна."
        member_ids = list(dict.fromkeys(int(m) for m in member_ids))
        if len(member_ids) > MAX_TREASURY_PAY_RECIPIENTS:
            return False, f"Нэг гүйлгээнд дээд тал нь {MAX_TREASURY_PAY_RECIPIENTS} хүлээн авагч болно."
        eco = self.bot.get_cog("Economy")

        async def _credit(uid: int, amt: int):
            if eco is not None:
                await eco.update_balance(uid, guild_id, amt, apply_tax=False)
            else:
                row = await self.bot.db_manager.fetch_one(
                    "economy", {"user_id": str(uid), "guild_id": str(guild_id)}
                )
                cur = int(row.get("balance") or 0) if row else 0
                await self.bot.db_manager.update(
                    "economy",
                    {"user_id": str(uid), "guild_id": str(guild_id)},
                    {"balance": cur + amt},
                )

        async with await self._get_lock(self._treasury_locks, gid):
            before = await self.get_treasury_balance(gid)
            if before < amount:
                return False, f"Тэтгэвэрт хүрэлцэхүйц мөнгө байхгүй (одоо {_fmt_money(before)})."
            splits = allocate_dividend(amount, len(member_ids))
            applied = []
            try:
                for uid, amt in zip(member_ids, splits):
                    if amt <= 0:
                        continue
                    await _credit(uid, amt)
                    applied.append((uid, amt))
            except Exception as e:
                logger.warning("treasury_pay credit failed, rolling back: %s", e)
                for uid, amt in reversed(applied):
                    try:
                        await _credit(uid, -amt)
                    except Exception:
                        pass
                return False, "Гүйлгээ амжилтгүй боллоо — мөнгө буцаагдлаа."
            try:
                after = before - amount
                await self._set_treasury(gid, after)
            except Exception as e:
                logger.warning("treasury debit failed, rolling back: %s", e)
                for uid, amt in reversed(applied):
                    try:
                        await _credit(uid, -amt)
                    except Exception:
                        pass
                return False, "Гүйлгээ амжилтгүй боллоо — мөнгө буцаагдлаа."
            await self.add_ledger(
                guild_id=gid, user_id=None, actor_id=str(actor_id),
                transaction_type="treasury_payment", amount=-amount,
                treasury_before=before, treasury_after=after,
                reason=reason or None, metadata=json.dumps(list(member_ids)),
            )
            for uid, amt in zip(member_ids, splits):
                if amt > 0:
                    await self.add_ledger(
                        guild_id=gid, user_id=str(uid), actor_id=str(actor_id),
                        transaction_type="treasury_payout", amount=amt,
                        reason=reason or None,
                    )
        return True, f"✅ Тэтгэвэрээс {_fmt_money(amount)} шилжүүллээ."

    # ------------------------------------------------------------------
    # tax distribution
    # ------------------------------------------------------------------
    async def distribute_tax(self, guild_id, tax: int) -> int:
        """Distribute collected tax to configured recipients (apply_tax=False
        -> no recursive taxation). Returns the amount credited to users."""
        tax = int(tax or 0)
        if tax <= 0:
            return 0
        gid = str(guild_id)
        async with await self._get_lock(self._tax_locks, gid):
            if not await self.is_government_active(gid):
                return 0
            guild = self.bot.get_guild(int(gid))
            recipients = await self.get_recipients(gid)
            if not recipients or recipient_total(recipients) != 100:
                if not await self.credit_treasury(gid, tax, reason="tax_fallback_unconfigured"):
                    logger.warning("treasury fallback failed gid=%s tax=%s", gid, tax)
                return 0
            if guild is None:
                if not await self.credit_treasury(gid, tax, reason="tax_fallback_no_guild"):
                    logger.warning("treasury fallback failed gid=%s tax=%s", gid, tax)
                return 0
            co_owners = await self.get_co_owner_ids(gid)
            plan = build_distribution_plan(guild, recipients, co_owners, tax)
            distributed = 0
            eco = self.bot.get_cog("Economy")
            for uid, amount, _label in plan["credits"]:
                if amount <= 0:
                    continue
                try:
                    if eco is not None:
                        await eco.update_balance(uid, guild_id, amount, apply_tax=False)
                    else:
                        row = await self.bot.db_manager.fetch_one(
                            "economy", {"user_id": str(uid), "guild_id": str(guild_id)}
                        )
                        cur = int(row.get("balance") or 0) if row else 0
                        await self.bot.db_manager.update(
                            "economy",
                            {"user_id": str(uid), "guild_id": str(guild_id)},
                            {"balance": cur + amount},
                        )
                    distributed += amount
                except Exception as e:
                    logger.warning("distribution credit failed uid=%s gid=%s: %s", uid, gid, e)
            if plan["treasury"] > 0:
                await self.credit_treasury(gid, plan["treasury"], reason="tax_distribution_share")
            await self.add_ledger(
                guild_id=gid, transaction_type="tax_collected", amount=tax,
                reason="distribution",
                metadata=f"distributed={distributed},treasury={plan['treasury']}",
            )
            return distributed

    async def distribution_preview(self, guild_id, tax: int) -> Dict[str, Any]:
        tax = int(tax or 0)
        gid = str(guild_id)
        guild = self.bot.get_guild(int(gid))
        recipients = await self.get_recipients(gid)
        active = bool(recipients and recipient_total(recipients) == 100)
        if guild is None:
            return {"ok": False, "lines": ["❌ Гильд олдсонгүй."], "tax": tax, "active": active}
        plan = build_distribution_plan(
            guild, recipients, await self.get_co_owner_ids(gid), tax
        )
        lines = []
        for uid, amt, _label in plan["credits"]:
            lines.append(f"• <@{uid}> → **{_fmt_money(amt)}**")
        lines.append(f"• 🏛️ Тэтгэвэр → **{_fmt_money(plan['treasury'])}**")
        return {"ok": True, "lines": lines or ["— хуваарилалт хоосон —"], "tax": tax, "active": active}

    # ------------------------------------------------------------------
    # ledger (best-effort — never corrupts the primary transaction)
    # ------------------------------------------------------------------
    async def add_ledger(self, *, guild_id, transaction_type, amount=0, user_id=None,
                         actor_id=None, treasury_before=None, treasury_after=None,
                         balance_before=None, balance_after=None, reason=None,
                         metadata=None) -> None:
        try:
            await self.bot.db_manager.insert(
                LEDGER_TABLE,
                {
                    "guild_id": str(guild_id),
                    "user_id": str(user_id) if user_id is not None else None,
                    "actor_id": str(actor_id) if actor_id is not None else None,
                    "transaction_type": transaction_type,
                    "amount": int(amount),
                    "treasury_before": treasury_before,
                    "treasury_after": treasury_after,
                    "balance_before": balance_before,
                    "balance_after": balance_after,
                    "reason": reason,
                    "metadata": metadata,
                    "created_at": int(time.time()),
                }
            )
        except Exception as e:
            logger.warning("ledger write failed (guild=%s txn=%s): %s", guild_id, transaction_type, e)

    async def get_ledger(self, guild_id, page: int = 0, per: int = LEDGER_PER_PAGE) -> List[Dict[str, Any]]:
        page = max(0, int(page or 0))
        rows = await self.bot.db_manager.fetch_all(
            LEDGER_TABLE,
            {"guild_id": str(guild_id)},
            order_by="created_at",
            desc=True,
            limit=per,
            offset=page * per,
        )
        out = []
        for r in rows or []:
            try:
                out.append({
                    "id": r.get("id"),
                    "user_id": r.get("user_id"),
                    "actor_id": r.get("actor_id"),
                    "transaction_type": r.get("transaction_type"),
                    "amount": int(r.get("amount") or 0),
                    "reason": r.get("reason"),
                    "metadata": r.get("metadata"),
                    "created_at": int(r.get("created_at") or 0),
                })
            except (KeyError, TypeError, ValueError):
                continue
        return out

    async def ledger_stats_today(self, guild_id) -> Tuple[int, int]:
        gid = str(guild_id)
        start = int(time.time()) - (int(time.time()) % 86400)
        rows = await self.bot.db_manager.fetch_safe(LEDGER_TABLE, {"guild_id": gid})
        income = 0
        expense = 0
        for r in rows or []:
            try:
                if int(r.get("created_at") or 0) < start:
                    continue
                amt = int(r.get("amount") or 0)
                txn = r.get("transaction_type") or ""
                if txn in ("treasury_payment", "treasury_payout", "tax_distributed"):
                    if amt < 0:
                        expense += -amt
                    else:
                        expense += amt
                elif txn in ("treasury_deposit", "tax_collected"):
                    if amt > 0:
                        income += amt
            except (TypeError, ValueError):
                continue
        return income, expense

    # ------------------------------------------------------------------
    # reset
    # ------------------------------------------------------------------
    async def reset_guild_config(self, guild_id) -> str:
        gid = str(guild_id)
        await self.bot.db_manager.delete(ROLES_TABLE, {"guild_id": gid})
        await self.bot.db_manager.delete(MEMBERS_TABLE, {"guild_id": gid})
        await self.bot.db_manager.delete(RECIPIENTS_TABLE, {"guild_id": gid})
        await self.bot.db_manager.delete(JOBS_TABLE, {"guild_id": gid})
        await self.bot.db_manager.delete(ROLE_INCOME_TABLE, {"guild_id": gid})
        await self._save_settings(
            gid,
            government_enabled=False,
            tax_rate=DEFAULT_TAX_RATE,
            tax_enabled=True,
            treasury_public=False,
        )
        return "✅ Бүх тохиргоо шинэчлэгдсэн. Government систем унтарсан, татвар 10%, хүлээн авагч ба ажил хоосон."

    # ------------------------------------------------------------------
    # permissions
    # ------------------------------------------------------------------
    async def _has_government_role_id(self, guild, member, role_type) -> bool:
        if guild is None or member is None:
            return False
        role_id = await self.get_government_role(guild.id, role_type)
        if role_id is None:
            return False
        return any(getattr(r, "id", None) == role_id for r in getattr(member, "roles", ()))

    async def can_manage_government(self, interaction) -> bool:
        if interaction.guild is None:
            return False
        if interaction.user.id == interaction.guild.owner_id:
            return True
        if await self.is_co_owner_id(interaction.guild.id, interaction.user.id):
            return True
        for t in ("government_admin", "president"):
            if await self._has_government_role_id(interaction.guild, interaction.user, t):
                return True
        return False

    async def can_manage_economy(self, interaction) -> bool:
        if await self.can_manage_government(interaction):
            return True
        if interaction.guild is not None and await self._has_government_role_id(
            interaction.guild, interaction.user, "finance"
        ):
            return True
        return False

    async def can_manage_treasury(self, interaction) -> bool:
        return await self.can_manage_economy(interaction)

    async def can_view_treasury(self, interaction) -> bool:
        if await self.can_manage_treasury(interaction):
            return True
        if interaction.guild is not None and await self._has_government_role_id(
            interaction.guild, interaction.user, "tax_collector"
        ):
            return True
        return False

    async def compute_perms(self, interaction) -> GovPerms:
        p = GovPerms()
        if interaction.guild is None:
            return p
        p.owner = interaction.user.id == interaction.guild.owner_id
        p.co_owner = await self.is_co_owner_id(interaction.guild.id, interaction.user.id)
        p.government = p.owner or p.co_owner or await self.can_manage_government(interaction)
        p.economy = p.owner or p.co_owner or await self.can_manage_economy(interaction)
        p.treasury_manage = p.owner or p.co_owner or await self.can_manage_treasury(interaction)
        p.treasury_ro = await self.can_view_treasury(interaction)
        return p

    # ==================================================================
    # COMMANDS
    # ==================================================================
    @app_commands.command(name="government", description="🏛️ Засгийн газар: officials, roles, co-owners, toggle")
    @app_commands.guild_only()
    async def government_cmd(self, interaction: discord.Interaction):
        if not await self.can_manage_government(interaction):
            return await deny(interaction, "Зөвхөн сервер эзэмшигч, co-owner, Засгийн газрын админ эсвэл Ерөнхийлөгч ашиглаж болно.")
        perms = await self.compute_perms(interaction)
        view = GovernmentMainView(self, interaction, perms)
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="economy-config", description="⚙️ Эдийн засгийн тохиргоо: татвар, ажил, ролын орлого")
    @app_commands.guild_only()
    async def economy_config_cmd(self, interaction: discord.Interaction):
        if not await self.can_manage_economy(interaction):
            return await deny(interaction, "Зөвхөн сервер эзэмшигч, co-owner, Засгийн газрын админ, Ерөнхийлөгч эсвэл Сангийн сайд ашиглаж болно.")
        perms = await self.compute_perms(interaction)
        view = EconomyConfigView(self, interaction, perms)
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="treasury", description="🏦 Засгийн тэтгэвэр: үлдэгдэл, төлбөр, түүх, хуваарилалт")
    @app_commands.guild_only()
    async def treasury_cmd(self, interaction: discord.Interaction):
        perms = await self.compute_perms(interaction)
        if not perms.treasury_ro:
            return await deny(interaction, "Зөвхөн Сангийн сайд болон түүнээс дээш эрх нээж болно.")
        view = TreasuryView(self, interaction, perms)
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="economy", description="💰 Хэрэглэгчийн эдийн засгийн самбар")
    @app_commands.guild_only()
    async def economy_panel_cmd(self, interaction: discord.Interaction):
        view = EconomyPanelView(self, interaction, GovPerms())
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view)


async def deny(interaction: discord.Interaction, text: str) -> None:
    embed = discord.Embed(title="⛔ Эрх хүрэлцэхгүй", description=text, color=ERROR_COLOR)
    if not interaction.response.is_done():
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send(embed=embed, ephemeral=True)


# ======================================================================
# Shared UI base
# ======================================================================
class GovBase(View):
    def __init__(self, cog: Government, interaction: discord.Interaction,
                 perms: Optional[GovPerms] = None, timeout: int = 600):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.guild = interaction.guild
        self.guild_id = str(interaction.guild.id)
        self.opener_id = interaction.user.id
        self.member = interaction.user
        self.perms = perms or GovPerms()

    async def _respond_once(self, interaction, *, content=None, embed=None, view=None, ephemeral=True):
        if not interaction.response.is_done():
            await interaction.response.send_message(content=content, embed=embed, view=view, ephemeral=ephemeral)
        else:
            await interaction.followup.send(content=content, embed=embed, view=view, ephemeral=ephemeral)

    async def _swap(self, interaction, embed, view=None):
        if not interaction.response.is_done():
            try:
                await interaction.response.edit_message(embed=embed, view=view)
                return
            except Exception:
                pass
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            try:
                await interaction.followup.send(embed=embed, view=view)
            except Exception:
                pass

    async def _close(self, interaction):
        for item in self.children:
            item.disabled = True
        try:
            await interaction.response.edit_message(content="❌ Самбар хаагдлаа.", embed=None, view=None)
        except Exception:
            try:
                await interaction.edit_original_response(content="❌ Самбар хаагдлаа.", embed=None, view=None)
            except Exception:
                pass

    async def interaction_check(self, interaction) -> bool:
        if interaction.user.id != self.opener_id:
            await self._respond_once(
                interaction,
                embed=discord.Embed(title="⛔ Хандах боломжгүй", description="Энэ самбар өөр хэрэглэгчийнх юм.", color=ERROR_COLOR),
            )
            return False
        return True


class ErrorToast:
    """Small helper to send ephemeral error embeds from callbacks."""

    @staticmethod
    async def send(interaction, text: str) -> None:
        embed = discord.Embed(title="❌ Алдаа", description=text, color=ERROR_COLOR)
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)


class SwapConfirm(View):
    """Swap-based confirmation with a set-once guard (double-click safe).

    ``on_yes`` / ``on_no`` run after the confirm interaction is deferred, so
    they may use ``interaction.followup`` (toast) and
    ``interaction.edit_original_response`` (rebuild the parent panel).
    """

    def __init__(self, opener_id: int, on_yes, on_no=None, prompt: Optional[str] = None, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.opener_id = opener_id
        self.on_yes = on_yes
        self.on_no = on_no or (lambda interaction: None)
        self.prompt = prompt
        self.used = False

    async def interaction_check(self, interaction) -> bool:
        if interaction.user.id != self.opener_id:
            await interaction.response.send_message("⛔ Энэ самбар өөр хэрэглэгчийнх юм.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Тийм ✅", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: Button):
        if self.used:
            return await interaction.response.defer(ephemeral=True)
        self.used = True
        self.stop()
        await interaction.response.defer(ephemeral=True)
        await self.on_yes(interaction)

    @discord.ui.button(label="Үгүй ❌", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: Button):
        if self.used:
            return await interaction.response.defer(ephemeral=True)
        self.used = True
        self.stop()
        await interaction.response.defer(ephemeral=True)
        await self.on_no(interaction)


def render_recipients(recipients: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for r in sorted(recipients, key=lambda x: (-int(x["percentage"] or 0), str(x["recipient_type"]))):
        label = RECIPIENT_TYPE_LABELS.get(r["recipient_type"], r["recipient_type"])
        lines.append(f"{label}: **{int(r['percentage'] or 0)}%**")
    return lines


# ======================================================================
# /government — main panel
# ======================================================================
class GovernmentMainView(GovBase):
    async def build_embed(self) -> discord.Embed:
        settings = await self.cog.get_settings(self.guild_id)
        roles = await self.cog.get_government_roles(self.guild_id)
        co = await self.cog.get_co_owner_ids(self.guild_id)
        embed = discord.Embed(
            title="🏛️ Засгийн газар",
            description="Доорх товчлуураар officials, рол, co-owner ба тохиргоог удирдана уу.",
            color=GOLD_COLOR,
        )
        status = "✅ Идэвхтэй" if settings.get("government_enabled") else "⛔ Идэвхгүй"
        embed.add_field(name="🟢 Систем", value=f"{status}\nТатвар: **{settings.get('tax_rate')}%**", inline=True)
        embed.add_field(name="👥 Co-owners", value=str(len(co)), inline=True)
        role_lines = [
            f"{ROLE_TYPE_LABELS[t][0]}: {_role_mention(roles[t]) if roles.get(t) else '—'}"
            for t in ROLE_TYPE_ORDER
        ]
        add_box_field(embed, "🎭 ЗАСГИЙН ГАЗРЫН РОЛУУД", role_lines)
        embed.set_footer(text="Зөвхөн эрхтэй хэрэглэгч удирдана")
        return embed

    @discord.ui.button(label="👑 Officials", style=discord.ButtonStyle.blurple, row=0)
    async def officials(self, interaction: discord.Interaction, button: Button):
        view = OfficialsView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="🎭 Roles", style=discord.ButtonStyle.blurple, row=0)
    async def roles(self, interaction: discord.Interaction, button: Button):
        embed, view = await RolesView.build(self.cog, interaction, self.perms)
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="👥 Co-Owners", style=discord.ButtonStyle.blurple, row=0)
    async def co_owners(self, interaction: discord.Interaction, button: Button):
        embed, view = await CoOwnersView.build(self.cog, interaction, self.perms)
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="⚙️ Settings", style=discord.ButtonStyle.secondary, row=1)
    async def settings(self, interaction: discord.Interaction, button: Button):
        view = GovSettingsView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=1)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)


class OfficialsView(GovBase):
    async def build_embed(self) -> discord.Embed:
        roles = await self.cog.get_government_roles(self.guild_id)
        co = await self.cog.get_co_owner_ids(self.guild_id)
        embed = discord.Embed(
            title="👑 Officials",
            description="Засгийн газрын албан тушаалтнууд (рол нэрээс ID-аар хадгалагдана).",
            color=INFO_COLOR,
        )
        embed.add_field(name="👑 Сервер эзэмшигч", value=f"<@{self.guild.owner_id}>", inline=False)
        co_text = "\n".join(f"<@{uid}>" for uid in co) if co else "— байхгүй —"
        embed.add_field(name="👥 Co-owners", value=co_text, inline=False)
        for t in ROLE_TYPE_ORDER:
            rid = roles.get(t)
            if rid:
                role = self.guild.get_role(rid)
                members = [m for m in (getattr(role, "members", None) or []) if not getattr(m, "bot", False)]
                text = "\n".join(m.mention for m in members)[:1000] or f"<@&{rid}> (гишүүн байхгүй)"
            else:
                text = "Тохируулаагүй — /government → Roles"
            embed.add_field(name=ROLE_TYPE_LABELS[t][0], value=text, inline=False)
        return embed

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = GovernmentMainView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=1)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)


class RolesView(GovBase):
    def __init__(self, cog, interaction, perms, selected_type=None, selected_role=None):
        super().__init__(cog, interaction, perms)
        self.selected_type: Optional[str] = selected_type
        self.selected_role = selected_role

    @classmethod
    async def build(cls, cog, interaction, perms):
        view = cls(cog, interaction, perms)
        embed = await view.build_embed()
        return embed, view

    async def build_embed(self) -> discord.Embed:
        roles = await self.cog.get_government_roles(self.guild_id)
        embed = discord.Embed(
            title="🎭 Засгийн газрын ролууд",
            description="Төрөл ба Discord роль сонгоод **Тохируулах** дарна уу.\nРолыг **ID-аар** хадгална — нэр өөрчлөгдсөн ч ажилласаар байна.",
            color=INFO_COLOR,
        )
        lines = [
            f"{'✅' if roles.get(t) else '❌'} {ROLE_TYPE_LABELS[t][0]}: {_role_mention(roles[t]) if roles.get(t) else '—'}"
            for t in ROLE_TYPE_ORDER
        ]
        embed.add_field(name="Одоогийн тохиргоо", value="\n".join(lines), inline=False)
        sel_type = ROLE_TYPE_LABELS[self.selected_type][0] if self.selected_type else "—"
        sel_role = f"{getattr(self.selected_role, 'mention', '')}" if getattr(self.selected_role, "id", None) else "—"
        embed.add_field(name="Сонголт", value=f"Төрөл: **{sel_type}**\nРоль: {sel_role}", inline=False)
        return embed

    @discord.ui.select(
        placeholder="1️⃣ Ролын төрөл сонгох", row=0, min_values=1, max_values=1,
        options=[SelectOption(label=ROLE_TYPE_LABELS[t][0], value=t) for t in ROLE_TYPE_ORDER],
    )
    async def type_select(self, interaction: discord.Interaction, select: Select):
        self.selected_type = select.values[0]
        await self._respond_once(interaction, content="✔️ Төрөл сонгогдлоо.", ephemeral=True)

    @discord.ui.select(cls=RoleSelect, placeholder="2️⃣ Discord роль сонгох", row=1, min_values=1, max_values=1)
    async def role_pick(self, interaction: discord.Interaction, select: RoleSelect):
        self.selected_role = select.values[0]
        await self._respond_once(interaction, content="✔️ Роль сонгогдлоо.", ephemeral=True)

    @discord.ui.button(label="✅ Тохируулах", style=discord.ButtonStyle.green, row=2)
    async def set_btn(self, interaction: discord.Interaction, button: Button):
        if not self.selected_type:
            return await self._respond_once(interaction, content="❌ Эхлээд төрөл сонгоно уу.", ephemeral=True)
        if not getattr(self.selected_role, "id", None):
            return await self._respond_once(interaction, content="❌ Эхлээд Discord роль сонгоно уу.", ephemeral=True)
        await self.cog.set_government_role(self.guild_id, self.selected_type, self.selected_role.id, self.opener_id)
        await self._respond_once(
            interaction,
            content=f"✅ {ROLE_TYPE_LABELS[self.selected_type][0]} → {self.selected_role.mention}",
            ephemeral=True,
        )
        embed, view = await RolesView.build(self.cog, interaction, self.perms)
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="🗑️ Арилгах", style=discord.ButtonStyle.red, row=2)
    async def clear_btn(self, interaction: discord.Interaction, button: Button):
        if not self.selected_type:
            return await self._respond_once(interaction, content="❌ Эхлээд төрөл сонгоно уу.", ephemeral=True)
        await self.cog.clear_government_role(self.guild_id, self.selected_type)
        await self._respond_once(
            interaction,
            content=f"🗑️ {ROLE_TYPE_LABELS[self.selected_type][0]} арилгагдлаа.",
            ephemeral=True,
        )
        embed, view = await RolesView.build(self.cog, interaction, self.perms)
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = GovernmentMainView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)


class CoOwnersView(GovBase):
    def __init__(self, cog, interaction, perms):
        super().__init__(cog, interaction, perms)

    @classmethod
    async def build(cls, cog, interaction, perms):
        view = cls(cog, interaction, perms)
        embed = await view.build_embed()
        return embed, view

    async def build_embed(self) -> discord.Embed:
        co = await self.cog.get_co_owner_ids(self.guild_id)
        embed = discord.Embed(
            title="👥 Co-Owners",
            description="Зөвхөн **сервер эзэмшигч** co-owner нэмэх/хасах боломжтой.\nCo-owner нь Засгийн газрын бүх эрхтэй (хамгийн дээд түвшин).",
            color=INFO_COLOR,
        )
        if co:
            embed.description += "\n\n" + "\n".join(f"• <@{uid}>" for uid in co)
        else:
            embed.description += "\n\n— одоогоор co-owner байхгүй —"
        return embed

    @discord.ui.select(
        placeholder="➕ Нэмэх хэрэглэгч сонгох", row=0, min_values=1, max_values=1, cls=UserSelect,
    )
    async def add_select(self, interaction: discord.Interaction, select: UserSelect):
        if not self.perms.owner:
            return await self._respond_once(interaction, content="⛔ Зөвхөн сервер эзэмшигч co-owner нэмж чадна.", ephemeral=True)
        user = select.values[0]
        if user.id == self.guild.owner_id:
            return await self._respond_once(interaction, content="❌ Сервер эзэмшигч өөрөө co-owner байх шаардлагагүй.", ephemeral=True)
        ok, msg = await self.cog.add_co_owner(self.guild_id, user.id, self.opener_id)
        await self._respond_once(interaction, content=msg, ephemeral=True)
        embed, view = await CoOwnersView.build(self.cog, interaction, self.perms)
        await self._swap(interaction, embed, view)

    @discord.ui.select(
        placeholder="➖ Хасах co-owner сонгох", row=1, min_values=1, max_values=1, cls=UserSelect,
    )
    async def remove_select(self, interaction: discord.Interaction, select: UserSelect):
        if not self.perms.owner:
            return await self._respond_once(interaction, content="⛔ Зөвхөн сервер эзэмшигч co-owner хасаж чадна.", ephemeral=True)
        user = select.values[0]
        if user.id == self.guild.owner_id:
            return await self._respond_once(interaction, content="❌ Сервер эзэмшигч co-owner биш байна.", ephemeral=True)
        ok, msg = await self.cog.remove_co_owner(self.guild_id, user.id)
        await self._respond_once(interaction, content=msg, ephemeral=True)
        embed, view = await CoOwnersView.build(self.cog, interaction, self.perms)
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = GovernmentMainView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)


class GovSettingsView(GovBase):
    async def build_embed(self) -> discord.Embed:
        settings = await self.cog.get_settings(self.guild_id)
        embed = discord.Embed(
            title="⚙️ Засгийн газрын тохиргоо",
            description=(
                "Government систем асах үед татвар тохируулсан хүлээн авагчдад хуваарилагдана. "
                "Хүлээн авагч тохируулаагүй бол татвар Тэтгэвэрт орно (`/economy-config → Татвар`)."
            ),
            color=INFO_COLOR,
        )
        embed.add_field(
            name="🟢 Систем",
            value="✅ Идэвхтэй" if settings.get("government_enabled") else "⛔ Идэвхгүй (легаси татвар)",
            inline=True,
        )
        embed.add_field(name="🧾 Татвар", value=f"**{settings.get('tax_rate')}%**", inline=True)
        return embed

    @discord.ui.button(label="🔄 Систем асаах/унтраах", style=discord.ButtonStyle.primary, row=0)
    async def toggle(self, interaction: discord.Interaction, button: Button):
        settings = await self.cog.get_settings(self.guild_id)
        enabled = not settings.get("government_enabled")
        await self.cog._save_settings(self.guild_id, government_enabled=enabled)
        state = "асаагдлаа ✅" if enabled else "унтарлаа (легаси татвар руу буцлаа)"
        await self._respond_once(interaction, content=f"🟢 Government систем {state}.", ephemeral=True)
        view = GovSettingsView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = GovernmentMainView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=1)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)


# ======================================================================
# /economy-config — main panel
# ======================================================================
class EconomyConfigView(GovBase):
    async def build_embed(self) -> discord.Embed:
        c = self.cog
        settings = await c.get_settings(self.guild_id)
        recipients = await c.get_recipients(self.guild_id)
        jobs = await c.get_custom_jobs(self.guild_id)
        incomes = await c.get_role_incomes(self.guild_id)
        valid, total, _msg = validate_recipient_set(recipients)
        embed = discord.Embed(
            title="⚙️ Эдийн засгийн тохиргоо",
            description="Доорх товчлуураар татвар, ажил, ролын орлогыг удирдана уу.",
            color=INFO_COLOR,
        )
        embed.add_field(name="🧾 Татвар", value=f"**{settings.get('tax_rate')}%** · {'идэвхтэй' if settings.get('tax_enabled') else 'унтраасан'}", inline=True)
        embed.add_field(name="📊 Хуваарилалт", value=f"{total}% ({'✅' if valid else '⚠️'})", inline=True)
        embed.add_field(name="💼 Ажил", value=f"{len(jobs)} ширхэг", inline=True)
        embed.add_field(name="💰 Ролын орлого", value=f"{len(incomes)} тохиргоо", inline=True)
        embed.set_footer(text="Зөвхөн эрхтэй хэрэглэгч удирдана")
        return embed

    @discord.ui.button(label="🏛️ Татвар", style=discord.ButtonStyle.secondary, row=0)
    async def tax(self, interaction: discord.Interaction, button: Button):
        view = TaxPanelView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="💼 Ажил", style=discord.ButtonStyle.blurple, row=0)
    async def jobs(self, interaction: discord.Interaction, button: Button):
        embed, view = await JobsManagerView.build(self.cog, interaction, self.perms)
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="💰 Ролын орлого", style=discord.ButtonStyle.blurple, row=1)
    async def role_income(self, interaction: discord.Interaction, button: Button):
        view = RoleIncomeView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="⚙️ Тохиргоо", style=discord.ButtonStyle.secondary, row=1)
    async def settings(self, interaction: discord.Interaction, button: Button):
        view = EconomySettingsView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=2)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)


# ======================================================================
# Tax configuration
# ======================================================================
class TaxPanelView(GovBase):
    async def build_embed(self) -> discord.Embed:
        c = self.cog
        settings = await c.get_settings(self.guild_id)
        recipients = await c.get_recipients(self.guild_id)
        valid, total, msg = validate_recipient_set(recipients)
        treasury = await c.get_treasury_balance(self.guild_id)
        embed = discord.Embed(title="🏛️ Татварын тохиргоо", color=GOLD_COLOR)
        embed.add_field(name="🧾 Татварын хувь", value=f"**{settings.get('tax_rate')}%**", inline=True)
        embed.add_field(name="🔄 Төлөв", value="✅ Идэвхтэй" if settings.get("tax_enabled") else "❌ Унтраасан", inline=True)
        embed.add_field(name="🏦 Тэтгэвэр", value=_fmt_money(treasury), inline=True)
        if recipients:
            lines = []
            for r in sorted(recipients, key=lambda x: (-int(x["percentage"]), str(x["recipient_type"]))):
                label = RECIPIENT_TYPE_LABELS.get(r["recipient_type"], r["recipient_type"])
                ref = c.recipient_ref(self.guild, r)
                if r["recipient_type"] == "co_owner":
                    co = await c.get_co_owner_ids(self.guild_id)
                    ref = f"{len(co)} хүн" if co else "байхгүй → Тэтгэвэр"
                lines.append(f"{label} {ref}: **{r['percentage']}%**")
            embed.add_field(name="📊 Хүлээн авагчид", value="\n".join(lines)[:900] or "—", inline=False)
        else:
            embed.add_field(name="📊 Хүлээн авагчид", value="Тохируулаагүй — татвар Тэтгэвэрт орно.", inline=False)
        embed.add_field(name="📌 Төлөв", value=msg, inline=False)
        return embed

    @discord.ui.button(label="🔢 Татварын хувь", style=discord.ButtonStyle.primary, row=0)
    async def rate_btn(self, interaction: discord.Interaction, button: Button):
        modal = RateModal(self.cog, self.guild_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🧾 Хүлээн авагчид", style=discord.ButtonStyle.blurple, row=0)
    async def recipients_btn(self, interaction: discord.Interaction, button: Button):
        embed, view = await TaxRecipientsView.build(self.cog, interaction, self.perms)
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="🔄 Татвар асаах/унтраах", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_btn(self, interaction: discord.Interaction, button: Button):
        settings = await self.cog.get_settings(self.guild_id)
        enabled = not settings.get("tax_enabled")
        await self.cog._save_settings(self.guild_id, tax_enabled=enabled)
        state = "асаагдлаа" if enabled else "унтрааллаа (татвар авахгүй)"
        await self._respond_once(interaction, content=f"🧾 Татвар {state}.", ephemeral=True)
        view = TaxPanelView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="🏛️ Treasury Share", style=discord.ButtonStyle.secondary, row=1)
    async def treasury_share_btn(self, interaction: discord.Interaction, button: Button):
        modal = TreasuryShareModal(self.cog, self.guild_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🗑️ Reset", style=discord.ButtonStyle.red, row=2)
    async def reset_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="🗑️ Татварын тохиргоо reset хийх үү?",
            description="Бүх хүлээн авагч устгагдаж татвар 10% болно.",
            color=WARNING_COLOR,
        )
        confirm = SwapConfirm(
            self.opener_id,
            on_yes=self._do_reset,
            on_no=self._rebuild,
        )
        await self._swap(interaction, embed, confirm)

    async def _do_reset(self, interaction) -> None:
        await self.cog.clear_recipients(self.guild_id)
        await self.cog._save_settings(self.guild_id, tax_rate=DEFAULT_TAX_RATE, tax_enabled=True)
        await self._respond_once(interaction, content="✅ Татвар 10%, хүлээн авагч хоосон боллоо.", ephemeral=True)
        await self._rebuild(interaction)

    async def _rebuild(self, interaction) -> None:
        view = TaxPanelView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            pass

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = EconomyConfigView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)


class RateModal(Modal, title="Татварын хувь тохируулах"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = str(guild_id)
        self.add_item(TextInput(label="Хувь (0-100)", placeholder="10", required=True, max_length=3))

    async def on_submit(self, interaction: discord.Interaction):
        pct = parse_pct(self.children[0].value)
        if pct is None:
            return await self._respond_once(interaction, "❌ 0-100 хооронд бүхэл тоо оруулна уу.")
        await self.cog._save_settings(self.guild_id, tax_rate=pct)
        await self._respond_once(interaction, f"✅ Татварын хувь {pct}% боллоо.")
        await self._rebuild(interaction)

    async def _respond_once(self, interaction, content: str) -> None:
        await interaction.response.send_message(content, ephemeral=True)

    async def _rebuild(self, interaction) -> None:
        view = TaxPanelView(self.cog, interaction, await self.cog.compute_perms(interaction))
        embed = await view.build_embed()
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            pass


class TreasuryShareModal(Modal, title="Treasury Share"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = str(guild_id)
        self.add_item(TextInput(label="Тэтгэвэрт орох хувь (0-100)", placeholder="50", required=True, max_length=3))

    async def on_submit(self, interaction: discord.Interaction):
        pct = parse_pct(self.children[0].value)
        if pct is None:
            return await interaction.response.send_message("❌ 0-100 хооронд бүхэл тоо оруулна уу.", ephemeral=True)
        ok, msg = await self.cog.set_recipient(self.guild_id, "treasury", 0, pct, interaction.user.id)
        await interaction.response.send_message(msg, ephemeral=True)
        view = TaxPanelView(self.cog, interaction, await self.cog.compute_perms(interaction))
        embed = await view.build_embed()
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            pass


class TaxRecipientsView(GovBase):
    def __init__(self, cog, interaction, perms):
        super().__init__(cog, interaction, perms)
        self.add_type: Optional[str] = None
        self.add_user_id: Optional[int] = None
        self.add_role_id: Optional[int] = None
        self.removing_key: Optional[str] = None

    @classmethod
    async def build(cls, cog, interaction, perms):
        view = cls(cog, interaction, perms)
        embed = await view.build_embed()
        view._attach_dynamic_items()
        return embed, view

    def _attach_dynamic_items(self):
        async def _remove_cb(interaction, select):
            self.removing_key = select.values[0]
            await self._respond_once(interaction, content="✔️ Устгах хүлээн авагч сонгогдлоо.", ephemeral=True)

        recipients = []
        try:
            rows = self._recipients
        except AttributeError:
            rows = []
        for r in rows:
            label = RECIPIENT_TYPE_LABELS.get(r["recipient_type"], r["recipient_type"])
            ref = self.cog.recipient_ref(self.guild, r) or ""
            opts_label = f"{label} {ref} {r['percentage']}%".strip()
            recipients.append(SelectOption(label=opts_label[:99], value=f"{r['recipient_type']}:{r['recipient_key']}"))
        if not recipients:
            recipients = [SelectOption(label="— хүлээн авагч байхгүй —", value="__none__")]
        sel = Select(placeholder="🗑️ Устгах хүлээн авагч сонгох", options=recipients[:20], row=3, min_values=1, max_values=1)
        sel.callback = _remove_cb
        self.add_item(sel)

    async def build_embed(self) -> discord.Embed:
        c = self.cog
        recipients = await c.get_recipients(self.guild_id)
        valid, total, msg = validate_recipient_set(recipients)
        embed = discord.Embed(
            title="🧾 Хүлээн авагчид",
            description="1) Төрөл сонгох · 2) Хэрэглэгч/Роль сонгох · 3) Хувь оруулах.\n`0%` оруулбал хасагдана.",
            color=INFO_COLOR,
        )
        if recipients:
            lines = []
            for r in sorted(recipients, key=lambda x: (-int(x["percentage"]), str(x["recipient_type"]))):
                label = RECIPIENT_TYPE_LABELS.get(r["recipient_type"], r["recipient_type"])
                ref = c.recipient_ref(self.guild, r)
                if r["recipient_type"] == "co_owner":
                    co = await c.get_co_owner_ids(self.guild_id)
                    ref = f"{len(co)} хүн" if co else "байхгүй → Тэтгэвэр"
                lines.append(f"{label} {ref}: **{r['percentage']}%**")
            embed.add_field(name="📊 Хуваарилалт", value="\n".join(lines)[:900], inline=False)
        else:
            embed.add_field(name="📊 Хуваарилалт", value="Хоосон — татвар бүхэлдээ Тэтгэвэрт орно.", inline=False)
        embed.add_field(name="📌 Төлөв", value=msg, inline=False)
        return embed

    @discord.ui.select(
        placeholder="1️⃣ Төрөл сонгох", row=0, min_values=1, max_values=1,
        options=[SelectOption(label=RECIPIENT_TYPE_LABELS[t], value=t) for t in RECIPIENT_TYPE_LABELS],
    )
    async def type_select(self, interaction: discord.Interaction, select: Select):
        self.add_type = select.values[0]
        await self._respond_once(interaction, content=f"✔️ Төрөл: {RECIPIENT_TYPE_LABELS[self.add_type]}", ephemeral=True)

    @discord.ui.select(cls=UserSelect, placeholder="2a. Хэрэглэгч сонгох", row=1, min_values=1, max_values=1)
    async def user_select(self, interaction: discord.Interaction, select: UserSelect):
        if self.add_type not in ("user",):
            return await self._respond_once(interaction, content="❌ Эхлээд `🧑 Хэрэглэгч` төрөл сонгоно уу.", ephemeral=True)
        self.add_user_id = select.values[0].id
        await self._respond_once(interaction, content=f"✔️ Хэрэглэгч <@{self.add_user_id}> сонгогдлоо.", ephemeral=True)

    @discord.ui.select(cls=RoleSelect, placeholder="2b. Роль сонгох", row=2, min_values=1, max_values=1)
    async def role_select(self, interaction: discord.Interaction, select: RoleSelect):
        if self.add_type != "role":
            return await self._respond_once(interaction, content="❌ Эхлээд `🎭 Роль` төрөл сонгоно уу.", ephemeral=True)
        self.add_role_id = select.values[0].id
        await self._respond_once(interaction, content=f"✔️ Роль <@&{self.add_role_id}> сонгогдлоо.", ephemeral=True)

    @discord.ui.button(label="➕ Хувь оруулах", style=discord.ButtonStyle.green, row=4)
    async def add_btn(self, interaction: discord.Interaction, button: Button):
        if not self.add_type:
            return await self._respond_once(interaction, content="❌ Эхлээд төрөл сонгоно уу.", ephemeral=True)
        key = 0
        if self.add_type == "user":
            if self.add_user_id is None:
                return await self._respond_once(interaction, content="❌ Хэрэглэгч сонгоно уу.", ephemeral=True)
            key = self.add_user_id
        if self.add_type == "role":
            if self.add_role_id is None:
                return await self._respond_once(interaction, content="❌ Роль сонгоно уу.", ephemeral=True)
            key = self.add_role_id
        modal = RecipientPctModal(self.cog, self.guild_id, self.perms)
        modal.type_value = self.add_type
        modal.key_value = key
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🗑️ Устгах", style=discord.ButtonStyle.red, row=4)
    async def remove_btn(self, interaction: discord.Interaction, button: Button):
        if not self.removing_key or self.removing_key == "__none__":
            return await self._respond_once(interaction, content="❌ Эхлээд устгах хүлээн авагчийг сонгоно уу.", ephemeral=True)
        rtype, rkey = self.removing_key.split(":", 1)
        await self.cog.remove_recipient(self.guild_id, rtype, rkey)
        await self._respond_once(interaction, content="🗑️ Устгагдлаа.", ephemeral=True)
        embed, view = await TaxRecipientsView.build(self.cog, interaction, self.perms)
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="🧹 Бүгд", style=discord.ButtonStyle.secondary, row=4)
    async def clear_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="🧹 Бүх хүлээн авагчийг устгах уу?",
            description="Татвар дараа нь бүхэлдээ Тэтгэвэрт орно.",
            color=WARNING_COLOR,
        )
        confirm = SwapConfirm(
            self.opener_id,
            on_yes=self._do_clear,
            on_no=self._rebuild,
        )
        await self._swap(interaction, embed, confirm)

    async def _do_clear(self, interaction) -> None:
        await self.cog.clear_recipients(self.guild_id)
        await self._respond_once(interaction, content="🧹 Бүх хүлээн авагч устгагдлаа.", ephemeral=True)
        await self._rebuild(interaction)

    async def _rebuild(self, interaction) -> None:
        embed, view = await TaxRecipientsView.build(self.cog, interaction, self.perms)
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            pass

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=4)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = TaxPanelView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)


class RecipientPctModal(Modal, title="Хувь тохируулах"):
    def __init__(self, cog, guild_id, perms):
        super().__init__()
        self.cog = cog
        self.guild_id = str(guild_id)
        self.perms = perms
        self.type_value = "treasury"
        self.key_value = 0
        self.add_item(TextInput(label="Хувь (0-100)", placeholder="10", required=True, max_length=3))

    async def on_submit(self, interaction: discord.Interaction):
        pct = parse_pct(self.children[0].value)
        if pct is None:
            return await interaction.response.send_message("❌ 0-100 хооронд бүхэл тоо оруулна уу.", ephemeral=True)
        ok, msg = await self.cog.set_recipient(
            self.guild_id, self.type_value, self.key_value, pct, interaction.user.id
        )
        await interaction.response.send_message(msg, ephemeral=True)
        embed, view = await TaxRecipientsView.build(self.cog, interaction, self.perms)
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            pass


# ======================================================================
# Custom jobs
# ======================================================================
class JobsManagerView(GovBase):
    def __init__(self, cog, interaction, perms, page=0, jobs=None):
        super().__init__(cog, interaction, perms)
        self.page = max(0, int(page or 0))
        self.jobs = jobs or []
        self.selected_job_id: Optional[str] = None

    @classmethod
    async def build(cls, cog, interaction, perms, page=0):
        jobs = await cog.get_custom_jobs(interaction.guild.id)
        view = cls(cog, interaction, perms, page=page, jobs=jobs)
        view._attach_job_select()
        embed = await view.build_embed()
        return embed, view

    def _attach_job_select(self):
        start = self.page * JOBS_PER_PAGE
        slice_ = self.jobs[start:start + JOBS_PER_PAGE]
        opts = [
            SelectOption(
                label=f"{j['emoji']} {j['name'][:28]} (t.{j['required_level']})",
                value=str(j["id"]),
            )
            for j in slice_
        ]
        if not opts:
            opts = [SelectOption(label="— ажил байхгүй —", value="__none__")]

        async def _cb(interaction, select):
            v = select.values[0]
            self.selected_job_id = None if v == "__none__" else v
            await self._respond_once(interaction, content="✔️ Ажил сонгогдлоо.", ephemeral=True)

        sel = Select(placeholder="💼 Ажил сонгох", options=opts, row=0, min_values=1, max_values=1)
        sel.callback = _cb
        self.add_item(sel)

    async def _selected_job(self) -> Optional[Dict[str, Any]]:
        if not self.selected_job_id:
            return None
        return await self.cog.get_job(self.guild_id, self.selected_job_id)

    async def build_embed(self) -> discord.Embed:
        jobs = self.jobs
        total_pages = max(1, (len(jobs) + JOBS_PER_PAGE - 1) // JOBS_PER_PAGE)
        start = self.page * JOBS_PER_PAGE
        slice_ = jobs[start:start + JOBS_PER_PAGE]
        embed = discord.Embed(
            title="💼 Ажлын удирдлага",
            description=f"Хуудас **{self.page + 1}/{total_pages}** · нийт **{len(jobs)}** ажил",
            color=INFO_COLOR,
        )
        if slice_:
            lines = []
            for j in slice_:
                mark = "✅" if j["enabled"] else "⛔"
                role = _role_mention(j["required_role_id"]) if j.get("required_role_id") else "—"
                lines.append(
                    f"{mark} {j['emoji']} `{j['name']}` · tүв.{j['required_level']} · "
                    f"{j['salary_min']:,}-{j['salary_max']:,} ₮ · роль {role}"
                )
            embed.add_field(name="Ажлууд", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="Ажлууд", value="Одоогоор байхгүй.", inline=False)
        if self.selected_job_id:
            job = next((j for j in jobs if str(j.get("id")) == str(self.selected_job_id)), None)
            if job:
                embed.add_field(
                    name="Сонгосон",
                    value=f"{job['emoji']} `{job['name']}` · enabled={'✅' if job['enabled'] else '⛔'}",
                    inline=False,
                )
        return embed

    @discord.ui.button(label="➕ Нэмэх", style=discord.ButtonStyle.green, row=1)
    async def add_btn(self, interaction: discord.Interaction, button: Button):
        modal = JobModal(self.cog, self.guild_id, self.perms, job=None)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="✏️ Засах", style=discord.ButtonStyle.blurple, row=1)
    async def edit_btn(self, interaction: discord.Interaction, button: Button):
        job = await self._selected_job()
        if job is None:
            return await self._respond_once(interaction, content="❌ Эхлээд ажил сонгоно уу.", ephemeral=True)
        modal = JobModal(self.cog, self.guild_id, self.perms, job=job)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🗑️ Устгах", style=discord.ButtonStyle.red, row=1)
    async def delete_btn(self, interaction: discord.Interaction, button: Button):
        job = await self._selected_job()
        if job is None:
            return await self._respond_once(interaction, content="❌ Эхлээд ажил сонгоно уу.", ephemeral=True)
        embed = discord.Embed(
            title="🗑️ Ажил устгах уу?",
            description=f"`{job['name']}` ажил устгагдах болно. Энэ нь эргэлт буцалтгүй.",
            color=WARNING_COLOR,
        )
        confirm = SwapConfirm(self.opener_id, on_yes=self._make_deleter(job), on_no=self._rebuild)
        await self._swap(interaction, embed, confirm)

    def _make_deleter(self, job):
        async def _do(interaction) -> None:
            ok, msg = await self.cog.delete_job(self.guild_id, job["id"])
            await self._respond_once(interaction, content=msg, ephemeral=True)
            await self._rebuild(interaction)
        return _do

    @discord.ui.button(label="🔄 Идэвхжүүлэх", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_btn(self, interaction: discord.Interaction, button: Button):
        job = await self._selected_job()
        if job is None:
            return await self._respond_once(interaction, content="❌ Эхлээд ажил сонгоно уу.", ephemeral=True)
        ok, msg = await self.cog.toggle_job_enabled(self.guild_id, job["id"])
        await self._respond_once(interaction, content=msg, ephemeral=True)
        await self._rebuild(interaction)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary, row=2)
    async def prev_btn(self, interaction: discord.Interaction, button: Button):
        if self.page <= 0:
            return await self._respond_once(interaction, content="Эхний хуудас.", ephemeral=True)
        embed, view = await JobsManagerView.build(self.cog, interaction, self.perms, self.page - 1)
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary, row=2)
    async def next_btn(self, interaction: discord.Interaction, button: Button):
        total_pages = max(1, (len(self.jobs) + JOBS_PER_PAGE - 1) // JOBS_PER_PAGE)
        if self.page + 1 >= total_pages:
            return await self._respond_once(interaction, content="Сүүлийн хуудас.", ephemeral=True)
        embed, view = await JobsManagerView.build(self.cog, interaction, self.perms, self.page + 1)
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = EconomyConfigView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=2)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)

    async def _rebuild(self, interaction) -> None:
        embed, view = await JobsManagerView.build(self.cog, interaction, self.perms, self.page)
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            pass


class JobModal(Modal, title="Ажил"):
    def __init__(self, cog, guild_id, perms, job=None):
        super().__init__()
        self.cog = cog
        self.guild_id = str(guild_id)
        self.perms = perms
        self.job_id = job.get("id") if job else None
        default = job or {}
        self.add_item(TextInput(label="Нэр", default=default.get("name", ""), required=True, max_length=MAX_JOB_NAME_LEN))
        self.add_item(TextInput(label="Шаардлагатай түвшин", default=str(default.get("required_level") or 0), required=True, max_length=4))
        self.add_item(TextInput(label="Хамгийн бага цалин", default=str(default.get("salary_min") or 1800), required=True, max_length=10))
        self.add_item(TextInput(label="Хамгийн их цалин", default=str(default.get("salary_max") or 5000), required=True, max_length=10))
        role_default = f"<@&{default['required_role_id']}>" if default.get("required_role_id") else ""
        self.add_item(TextInput(label="Шаардлагатай роль (<@&id> / ID / \"-\")", default=role_default, required=False, max_length=32))

    async def on_submit(self, interaction: discord.Interaction):
        name = self.children[0].value
        level = parse_level(self.children[1].value)
        mn = parse_money(self.children[2].value, maximum=MAX_SALARY)
        mx = parse_money(self.children[3].value, maximum=MAX_SALARY)
        role = parse_role_ref(self.children[4].value)
        if level is None:
            return await interaction.response.send_message("❌ Түвшин бүхэл тоо байх ёстой.", ephemeral=True)
        if mn is None or mx is None:
            return await interaction.response.send_message(f"❌ Цалин 0-{MAX_SALARY:,} хооронд бүхэл тоо байна.", ephemeral=True)
        payload = {
            "name": name,
            "emoji": "💼",
            "required_level": level,
            "salary_min": mn,
            "salary_max": mx,
            "required_role_id": role,
        }
        if self.job_id is not None:
            ok, msg = await self.cog.update_job(self.guild_id, self.job_id, **payload)
        else:
            ok, msg = await self.cog.create_job(self.guild_id, payload, interaction.user.id)
        await interaction.response.send_message(msg, ephemeral=True)
        embed, view = await JobsManagerView.build(self.cog, interaction, self.perms)
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            pass


# ======================================================================
# Role income
# ======================================================================
class RoleIncomeView(GovBase):
    def __init__(self, cog, interaction, perms):
        super().__init__(cog, interaction, perms)
        self.selected_role_id: Optional[int] = None

    async def build_embed(self) -> discord.Embed:
        incomes = await self.cog.get_role_incomes(self.guild_id)
        embed = discord.Embed(
            title="💰 Ролын орлого",
            description="Роль сонгоод орлого тохируулна уу. Интервал 1 цагаас багагүй, 7 хоногоос хэтрэхгүй.",
            color=INFO_COLOR,
        )
        if incomes:
            lines = [
                f"• {_role_mention(inc['role_id'])} → {_fmt_money(inc['amount'])} / {fmt_interval(inc['interval_seconds'])}"
                for inc in incomes
            ]
            embed.add_field(name="Одоогийн тохиргоо", value="\n".join(lines)[:900], inline=False)
        else:
            embed.add_field(name="Одоогийн тохиргоо", value="— хоосон —", inline=False)
        if self.selected_role_id:
            inc = self.cog.get_role_income(incomes, self.selected_role_id)
            val = _role_mention(self.selected_role_id)
            if inc:
                val += f"\n💵 {_fmt_money(inc['amount'])} / {fmt_interval(inc['interval_seconds'])}"
            embed.add_field(name="Сонгосон", value=val, inline=False)
        return embed

    @discord.ui.select(cls=RoleSelect, placeholder="🎭 Роль сонгох", row=0, min_values=1, max_values=1)
    async def role_select(self, interaction: discord.Interaction, select: RoleSelect):
        self.selected_role_id = select.values[0].id
        await self._respond_once(interaction, content=f"✔️ Роль <@&{self.selected_role_id}> сонгогдлоо.", ephemeral=True)

    @discord.ui.button(label="💰 Тохируулах", style=discord.ButtonStyle.green, row=1)
    async def set_btn(self, interaction: discord.Interaction, button: Button):
        if not self.selected_role_id:
            return await self._respond_once(interaction, content="❌ Эхлээд роль сонгоно уу.", ephemeral=True)
        incomes = await self.cog.get_role_incomes(self.guild_id)
        inc = self.cog.get_role_income(incomes, self.selected_role_id)
        modal = RoleIncomeModal(self.cog, self.guild_id, self.perms, self.selected_role_id, inc)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🗑️ Устгах", style=discord.ButtonStyle.red, row=1)
    async def remove_btn(self, interaction: discord.Interaction, button: Button):
        if not self.selected_role_id:
            return await self._respond_once(interaction, content="❌ Эхлээд роль сонгоно уу.", ephemeral=True)
        embed = discord.Embed(
            title="🗑️ Ролын орлого устгах уу?",
            description=f"{_role_mention(self.selected_role_id)} ролын орлого устгагдах болно.",
            color=WARNING_COLOR,
        )
        confirm = SwapConfirm(self.opener_id, on_yes=self._make_remover(), on_no=self._rebuild)
        await self._swap(interaction, embed, confirm)

    def _make_remover(self):
        async def _do(interaction) -> None:
            ok, msg = await self.cog.remove_role_income(self.guild_id, self.selected_role_id)
            self.selected_role_id = None
            await self._respond_once(interaction, content=msg, ephemeral=True)
            await self._rebuild(interaction)
        return _do

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = EconomyConfigView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=2)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)

    async def _rebuild(self, interaction) -> None:
        view = RoleIncomeView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            pass


class RoleIncomeModal(Modal, title="Ролын орлого"):
    def __init__(self, cog, guild_id, perms, role_id, inc=None):
        super().__init__()
        self.cog = cog
        self.guild_id = str(guild_id)
        self.perms = perms
        self.role_id = role_id
        default_hours = (inc["interval_seconds"] // 3600) if inc else 1
        self.add_item(TextInput(
            label="Дүн (₮)",
            default=str(inc["amount"]) if inc else "500",
            required=True,
            max_length=10,
        ))
        self.add_item(TextInput(label="Интервал (цаг, 1-168)", default=str(default_hours), required=True, max_length=3))

    async def on_submit(self, interaction: discord.Interaction):
        amount = parse_money(self.children[0].value, maximum=MAX_ROLE_INCOME_AMOUNT)
        hours = _parse_int(self.children[1].value)
        if amount is None:
            return await interaction.response.send_message(
                f"❌ Дүн {MIN_ROLE_INCOME_AMOUNT:,}-{MAX_ROLE_INCOME_AMOUNT:,} ₮ хооронд байна.", ephemeral=True
            )
        if hours is None:
            return await interaction.response.send_message("❌ Цаг бүхэл тоо байх ёстой.", ephemeral=True)
        interval = hours * 3600
        if not (MIN_ROLE_INCOME_INTERVAL <= interval <= MAX_ROLE_INCOME_INTERVAL):
            return await interaction.response.send_message(
                "❌ Интервал 1 цагаас багагүй, 7 хоногоос хэтрэхгүй байна.", ephemeral=True
            )
        ok, msg = await self.cog.set_role_income(self.guild_id, self.role_id, amount, interval, interaction.user.id)
        await interaction.response.send_message(msg, ephemeral=True)
        view = RoleIncomeView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            pass


# ======================================================================
# Economy settings (treasury visibility / full reset)
# ======================================================================
class EconomySettingsView(GovBase):
    async def build_embed(self) -> discord.Embed:
        settings = await self.cog.get_settings(self.guild_id)
        embed = discord.Embed(
            title="⚙️ Эдийн засгийн тохиргоо",
            description="Тэтгэвэрийн харагдац болон бүрэн reset эндээс.",
            color=INFO_COLOR,
        )
        embed.add_field(
            name="🏦 Тэтгэвэр",
            value="👁 Нээлттэй (бүх хэрэглэгч харна)" if settings.get("treasury_public") else "🔒 Хувийн (зөвхөн эрхтэй)",
            inline=False,
        )
        embed.add_field(
            name="🟢 Систем",
            value="✅ Идэвхтэй" if settings.get("government_enabled") else "⛔ Идэвхгүй",
            inline=True,
        )
        embed.add_field(name="🧾 Татвар", value=f"**{settings.get('tax_rate')}%**", inline=True)
        return embed

    @discord.ui.button(label="👁 Тэтгэвэр нээлттэй/хувийн", style=discord.ButtonStyle.primary, row=0)
    async def toggle_treasury(self, interaction: discord.Interaction, button: Button):
        settings = await self.cog.get_settings(self.guild_id)
        public = not settings.get("treasury_public")
        await self.cog._save_settings(self.guild_id, treasury_public=public)
        state = "нээлттэй 👁" if public else "хувийн 🔒"
        await self._respond_once(interaction, content=f"🏦 Тэтгэвэр {state} боллоо.", ephemeral=True)
        view = EconomySettingsView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="🗑️ Бүгдийг reset", style=discord.ButtonStyle.red, row=1)
    async def reset_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="🗑️ Бүгдийг reset хийх үү?",
            description="Ролууд, co-owners, хүлээн авагчид, ажлууд, ролын орлого бүгд устаж систем унтрах болно.",
            color=WARNING_COLOR,
        )
        confirm = SwapConfirm(self.opener_id, on_yes=self._do_reset, on_no=self._rebuild)
        await self._swap(interaction, embed, confirm)

    async def _do_reset(self, interaction) -> None:
        msg = await self.cog.reset_guild_config(self.guild_id)
        await self._respond_once(interaction, content=msg, ephemeral=True)
        await self._rebuild(interaction)

    async def _rebuild(self, interaction) -> None:
        view = EconomySettingsView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            pass

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = EconomyConfigView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=1)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)


# ======================================================================
# /treasury
# ======================================================================
class TreasuryView(GovBase):
    async def build_embed(self) -> discord.Embed:
        c = self.cog
        settings = await c.get_settings(self.guild_id)
        balance = await c.get_treasury_balance(self.guild_id)
        income, expense = await c.ledger_stats_today(self.guild_id)
        recipients = await c.get_recipients(self.guild_id)
        valid, total, msg = validate_recipient_set(recipients)
        embed = discord.Embed(title="🏦 Тэтгэвэр", color=GOLD_COLOR)
        embed.add_field(name="💰 Үлдэгдэл", value=f"**{_fmt_money(balance)}**", inline=True)
        embed.add_field(name="📥 Өнөөдөр орсон", value=_fmt_money(income), inline=True)
        embed.add_field(name="📤 Өнөөдөр гарсан", value=_fmt_money(expense), inline=True)
        embed.add_field(name="📊 Хуваарилалт", value=f"{total}% ({'✅' if valid else '⚠️'})", inline=True)
        embed.add_field(name="🟢 Систем", value="✅ Идэвхтэй" if settings.get("government_enabled") else "⛔ Идэвхгүй", inline=True)
        embed.set_footer(text=msg)
        return embed

    @discord.ui.button(label="💸 Төлбөр", style=discord.ButtonStyle.green, row=0)
    async def pay_btn(self, interaction: discord.Interaction, button: Button):
        if not self.perms.treasury_manage:
            return await self._respond_once(interaction, content="⛔ Зөвхөн Сангийн сайд болон түүнээс дээш эрх.", ephemeral=True)
        view = PayTargetView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="📜 Түүх", style=discord.ButtonStyle.blurple, row=0)
    async def history_btn(self, interaction: discord.Interaction, button: Button):
        if not self.perms.treasury_manage:
            return await self._respond_once(interaction, content="⛔ Зөвхөн Сангийн сайд болон түүнээс дээш эрх.", ephemeral=True)
        embed, view = await TreasuryHistoryView.build(self.cog, interaction, self.perms)
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="📊 Хуваарилалт", style=discord.ButtonStyle.secondary, row=1)
    async def dist_btn(self, interaction: discord.Interaction, button: Button):
        if not self.perms.treasury_manage:
            return await self._respond_once(interaction, content="⛔ Зөвхөн Сангийн сайд болон түүнээс дээш эрх.", ephemeral=True)
        view = DistributionView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=1)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)


class PayTargetView(GovBase):
    def __init__(self, cog, interaction, perms):
        super().__init__(cog, interaction, perms)
        self.user_ids: List[int] = []
        self.role_id: Optional[int] = None

    async def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="💸 Тэтгэвэрээс төлбөр",
            description="Хэрэглэгч(д) эсвэл роль сонгоод **Төлбөр хийх**. Нэг дүнг сонгосон хүмүүст тэнцүү хуваана.",
            color=INFO_COLOR,
        )
        parts = []
        if self.user_ids:
            parts.append("🧑 " + ", ".join(f"<@{uid}>" for uid in self.user_ids[:10]))
        if self.role_id:
            parts.append(f"🎭 {_role_mention(self.role_id)} (гишүүд)")
        embed.add_field(name="Сонгосон", value="\n".join(parts) or "— юу ч сонгоогүй —", inline=False)
        return embed

    @discord.ui.select(cls=UserSelect, placeholder="🧑 Хэрэглэгч(д) сонгох (дээд тал 10)", row=0, min_values=1, max_values=10)
    async def user_select(self, interaction: discord.Interaction, select: UserSelect):
        self.user_ids = [m.id for m in select.values]
        await self._respond_once(interaction, content=f"✔️ {len(self.user_ids)} хэрэглэгч сонгогдлоо.", ephemeral=True)

    @discord.ui.select(cls=RoleSelect, placeholder="🎭 Роль сонгох (бүх гишүүд)", row=1, min_values=0, max_values=1)
    async def role_select(self, interaction: discord.Interaction, select: RoleSelect):
        self.role_id = select.values[0].id if select.values else None
        await self._respond_once(interaction, content=f"✔️ Роль {_role_mention(self.role_id)} сонгогдлоо." if self.role_id else "Роль хасагдлаа.", ephemeral=True)

    @discord.ui.button(label="💸 Төлбөр хийх", style=discord.ButtonStyle.green, row=2)
    async def pay_btn(self, interaction: discord.Interaction, button: Button):
        member_ids = list(self.user_ids)
        if self.role_id:
            role = self.guild.get_role(self.role_id)
            if role is not None:
                member_ids += [m.id for m in role.members if not getattr(m, "bot", False)]
        member_ids = list(dict.fromkeys(member_ids))
        if not member_ids:
            return await self._respond_once(interaction, content="❌ Хэнд төлөхийг сонгоно уу.", ephemeral=True)
        confirm = TreasuryPayConfirm(self.cog, self.guild_id, self.perms, member_ids)
        await interaction.response.send_modal(confirm)

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = TreasuryView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=2)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)


class TreasuryPayConfirm(Modal, title="Тэтгэвэрээс төлбөр"):
    def __init__(self, cog, guild_id, perms, member_ids):
        super().__init__()
        self.cog = cog
        self.guild_id = str(guild_id)
        self.perms = perms
        self.member_ids = member_ids
        self.add_item(TextInput(label="Нийт дүн (₮)", placeholder="10000", required=True, max_length=14))
        self.add_item(TextInput(label="Шалтгаан (опциональ)", placeholder="Шагнал / Тэтгэвэр", required=False, max_length=80))

    async def on_submit(self, interaction: discord.Interaction):
        amount = parse_money(self.children[0].value, maximum=MAX_TREASURY_PAY_AMOUNT)
        if amount is None:
            return await interaction.response.send_message(
                f"❌ Дүн эерэг бүхэл тоо, дээд тал {MAX_TREASURY_PAY_AMOUNT:,} байна.", ephemeral=True
            )
        reason = (self.children[1].value or "").strip()[:80] or None
        ok, msg = await self.cog.treasury_pay(self.guild_id, self.member_ids, amount, reason, interaction.user.id)
        await interaction.response.send_message(msg, ephemeral=True)
        view = TreasuryView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            pass


class TreasuryHistoryView(GovBase):
    def __init__(self, cog, interaction, perms, page=0):
        super().__init__(cog, interaction, perms)
        self.page = max(0, int(page or 0))

    @classmethod
    async def build(cls, cog, interaction, perms, page=0):
        view = cls(cog, interaction, perms, page=page)
        embed = await view.build_embed()
        return embed, view

    async def build_embed(self) -> discord.Embed:
        rows = await self.cog.get_ledger(self.guild_id, self.page)
        embed = discord.Embed(
            title="📜 Тэтгэвэрийн түүх",
            description=f"Хуудас **{self.page + 1}** · '{self.guild.name}'",
            color=INFO_COLOR,
        )
        if not rows:
            embed.add_field(name="Бичлэг", value="— хоосон —", inline=False)
        for r in rows:
            icon = TXN_ICONS.get(r["transaction_type"], "📌")
            amt = r["amount"]
            sign = "-" if amt < 0 else "+" if amt > 0 else ""
            try:
                when = datetime.fromtimestamp(r["created_at"]).strftime("%m-%d %H:%M")
            except (TypeError, ValueError, OSError):
                when = "?"
            label = (r.get("reason") or r.get("metadata") or "—")[:70]
            embed.add_field(
                name=f"{icon} {r['transaction_type']}",
                value=f"{sign}{_fmt_money(abs(amt))} · {when}\n{label}",
                inline=False,
            )
        return embed

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary, row=0)
    async def prev_btn(self, interaction: discord.Interaction, button: Button):
        if self.page <= 0:
            return await self._respond_once(interaction, content="Эхний хуудас.", ephemeral=True)
        embed, view = await TreasuryHistoryView.build(self.cog, interaction, self.perms, self.page - 1)
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary, row=0)
    async def next_btn(self, interaction: discord.Interaction, button: Button):
        rows = await self.cog.get_ledger(self.guild_id, self.page)
        if len(rows) < LEDGER_PER_PAGE:
            return await self._respond_once(interaction, content="Сүүлийн хуудас.", ephemeral=True)
        embed, view = await TreasuryHistoryView.build(self.cog, interaction, self.perms, self.page + 1)
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=0)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = TreasuryView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=0)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)


class DistributionView(GovBase):
    async def build_embed(self) -> discord.Embed:
        c = self.cog
        recipients = await c.get_recipients(self.guild_id)
        valid, total, msg = validate_recipient_set(recipients)
        embed = discord.Embed(
            title="📊 Татварын хуваарилалт",
            description="Хүлээн авагчдын тохиргоо болон хуваарилалтын симуляци.",
            color=GOLD_COLOR,
        )
        if recipients:
            lines = []
            for r in sorted(recipients, key=lambda x: (-int(x["percentage"]), str(x["recipient_type"]))):
                label = RECIPIENT_TYPE_LABELS.get(r["recipient_type"], r["recipient_type"])
                ref = c.recipient_ref(self.guild, r)
                lines.append(f"{label} {ref}: **{r['percentage']}%**")
            embed.add_field(name="Хүлээн авагчид", value="\n".join(lines)[:900], inline=False)
        else:
            embed.add_field(name="Хүлээн авагчид", value="Байхгүй — татвар Тэтгэвэрт орно.", inline=False)
        embed.add_field(name="📌 Төлөв", value=msg, inline=False)
        return embed

    @discord.ui.button(label="📊 Симуляци", style=discord.ButtonStyle.primary, row=0)
    async def sim_btn(self, interaction: discord.Interaction, button: Button):
        modal = DistributionSimModal(self.cog, self.guild_id, self.perms)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = TreasuryView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=1)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)


class DistributionSimModal(Modal, title="Хуваарилалтын симуляци"):
    def __init__(self, cog, guild_id, perms):
        super().__init__()
        self.cog = cog
        self.guild_id = str(guild_id)
        self.perms = perms
        self.add_item(TextInput(label="Татварын дүн (₮)", placeholder="10000", required=True, max_length=12))

    async def on_submit(self, interaction: discord.Interaction):
        tax = _parse_int(self.children[0].value)
        if tax is None or tax <= 0:
            return await interaction.response.send_message("❌ Эерэг бүхэл тоо оруулна уу.", ephemeral=True)
        preview = await self.cog.distribution_preview(self.guild_id, tax)
        embed = discord.Embed(
            title=f"📊 Хуваарилалт — {_fmt_money(preview['tax'])}",
            description="\n".join(preview["lines"]),
            color=INFO_COLOR,
        )
        embed.set_footer(text="✅ Идэвхтэй хуваарилалт" if preview.get("active") else "⚠️ Хуваарилалт идэвхгүй (Тэтгэвэр рүү орно)")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        view = DistributionView(self.cog, interaction, self.perms)
        panel = await view.build_embed()
        try:
            await interaction.edit_original_response(embed=panel, view=view)
        except Exception:
            pass


# ======================================================================
# /economy — user panel
# ======================================================================
class EconomyPanelView(GovBase):
    async def build_embed(self) -> discord.Embed:
        c = self.cog
        eco = c.bot.get_cog("Economy")
        uid = self.opener_id
        gid = self.guild_id
        cash = await eco.get_balance(uid, gid) if eco else 0
        bank = await eco.get_bank(uid, gid) if eco and hasattr(eco, "get_bank") else 0
        settings = await c.get_settings(gid)
        gov_active = bool(settings.get("government_enabled"))
        legacy_rate = eco.transfer_tax_percent if eco else DEFAULT_TAX_RATE
        rate = settings.get("tax_rate") if gov_active else legacy_rate
        tax_state = "✅ Идэвхтэй" if settings.get("tax_enabled") else "❌ Унтраасан"

        level = 1
        if eco and hasattr(eco, "get_discord_level"):
            try:
                level = await eco.get_discord_level(uid, gid)
            except Exception:
                pass
        job = await c.resolve_user_job(gid, level, member=self.member)
        job_text = "—"
        if job:
            job_text = f"{job['emoji']} `{job['name']}` · {job['min']:,}-{job['max']:,} ₮"
        elif eco and hasattr(eco, "get_job_for_level"):
            _req, _j = eco.get_job_for_level(level)
            job_text = f"{_j['emoji']} `{_j['name']}` · {_j['min']:,}-{_j['max']:,} ₮ (легаси)"

        embed = discord.Embed(title="💰 Эдийн засгийн самбар", color=INFO_COLOR)
        embed.add_field(name="👛 Гар дээр", value=_fmt_money(cash), inline=True)
        embed.add_field(name="🏦 Банканд", value=_fmt_money(bank), inline=True)
        embed.add_field(name="🧾 Татвар", value=f"**{rate}%** · {tax_state}", inline=True)
        embed.add_field(name="💼 Ажил", value=job_text, inline=False)
        embed.add_field(name="🏛️ Government", value="✅ Идэвхтэй" if gov_active else "⛔ Идэвхгүй", inline=True)
        treasury = "—"
        if settings.get("treasury_public") or self.perms.treasury_ro:
            treasury = _fmt_money(await c.get_treasury_balance(gid))
        embed.add_field(name="🏦 Тэтгэвэр", value=treasury, inline=True)
        return embed

    @discord.ui.button(label="💼 Ажлууд", style=discord.ButtonStyle.blurple, row=0)
    async def jobs_btn(self, interaction: discord.Interaction, button: Button):
        view = JobsUserView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="🧾 Татвар", style=discord.ButtonStyle.blurple, row=0)
    async def tax_btn(self, interaction: discord.Interaction, button: Button):
        view = TaxInfoUserView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="🏛️ Засгийн газар", style=discord.ButtonStyle.blurple, row=0)
    async def gov_btn(self, interaction: discord.Interaction, button: Button):
        view = GovPublicView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=1)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)


class JobsUserView(GovBase):
    async def build_embed(self) -> discord.Embed:
        c = self.cog
        jobs = await c.get_custom_jobs(self.guild_id, enabled_only=True)
        level = 1
        eco = c.bot.get_cog("Economy")
        if eco and hasattr(eco, "get_discord_level"):
            try:
                level = await eco.get_discord_level(self.opener_id, self.guild_id)
            except Exception:
                pass
        embed = discord.Embed(title="💼 Ажлын жагсаалт", description=f"Таны түвшин: **{level}**", color=INFO_COLOR)
        if not jobs:
            embed.add_field(name="Custom ажлууд", value="— байхгүй — легаси ажлуудыг `/jobs`-аар харна уу.", inline=False)
        else:
            lines = []
            for j in jobs:
                qualify = "✅" if j["required_level"] <= level else "⛔"
                role_need = _role_mention(j["required_role_id"]) if j.get("required_role_id") else ""
                lines.append(
                    f"{qualify} {j['emoji']} `{j['name']}` · tүв.{j['required_level']} · "
                    f"{j['salary_min']:,}-{j['salary_max']:,} ₮ {role_need}"
                )
            embed.add_field(name="Custom ажлууд", value="\n".join(lines)[:900], inline=False)
        return embed

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = EconomyPanelView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=1)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)


class TaxInfoUserView(GovBase):
    async def build_embed(self) -> discord.Embed:
        c = self.cog
        settings = await c.get_settings(self.guild_id)
        gov_active = bool(settings.get("government_enabled"))
        eco = c.bot.get_cog("Economy")
        legacy_rate = eco.transfer_tax_percent if eco else DEFAULT_TAX_RATE
        embed = discord.Embed(title="🧾 Татварын мэдээлэл", color=GOLD_COLOR)
        if gov_active:
            rate = settings.get("tax_rate")
            state = "✅ Идэвхтэй" if settings.get("tax_enabled") else "❌ Унтраасан"
            recipients = await c.get_recipients(self.guild_id)
            valid, total, _msg = validate_recipient_set(recipients)
            embed.add_field(name="📊 Татварын хувь", value=f"**{rate}%** (орлогод)", inline=True)
            embed.add_field(name="🔄 Төлөв", value=state, inline=True)
            embed.add_field(name="📊 Хуваарилалт", value=f"{total}% ({'✅' if valid else '⚠️'})", inline=True)
            embed.add_field(name="🏛️ Горим", value="Government систем идэвхтэй — татвар хүлээн авагчдад хуваарилагдана.", inline=False)
        else:
            embed.add_field(name="📊 Татварын хувь", value=f"**{legacy_rate}%** (орлогод)", inline=True)
            embed.add_field(name="🏛️ Горим", value="Легаси: татвар `Ерөнхийлөгч`/`Захирал` ролт хэрэглэгчид очно. `/government`-аар шинэ системд шилжинэ.", inline=False)
        if settings.get("treasury_public") or self.perms.treasury_ro:
            embed.add_field(name="🏦 Тэтгэвэр", value=_fmt_money(await c.get_treasury_balance(self.guild_id)), inline=False)
        return embed

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = EconomyPanelView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=1)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)


class GovPublicView(GovBase):
    async def build_embed(self) -> discord.Embed:
        c = self.cog
        roles = await c.get_government_roles(self.guild_id)
        co = await c.get_co_owner_ids(self.guild_id)
        embed = discord.Embed(title="🏛️ Засгийн газар", description="Одоогийн officials ба ролуудын мэдээлэл.", color=INFO_COLOR)
        embed.add_field(name="👑 Сервер эзэмшигч", value=f"<@{self.guild.owner_id}>", inline=False)
        embed.add_field(name="👥 Co-owners", value=", ".join(f"<@{uid}>" for uid in co) or "—", inline=False)
        for t in ROLE_TYPE_ORDER:
            rid = roles.get(t)
            embed.add_field(
                name=ROLE_TYPE_LABELS[t][0],
                value=_role_mention(rid) if rid else "—",
                inline=False,
            )
        return embed

    @discord.ui.button(label="⬅️ Буцах", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        view = EconomyPanelView(self.cog, interaction, self.perms)
        embed = await view.build_embed()
        await self._swap(interaction, embed, view)

    @discord.ui.button(label="❌ Хаах", style=discord.ButtonStyle.red, row=1)
    async def close(self, interaction: discord.Interaction, button: Button):
        await self._close(interaction)


async def setup(bot):
    await bot.add_cog(Government(bot))