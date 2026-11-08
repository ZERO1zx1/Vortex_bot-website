import asyncio
import logging
import random
import time
import weakref
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View

from src.core.exceptions import DatabaseSchemaError, InsufficientFundsError
from src.ui.setup import ConfirmActionView, SetupPanel, SetupState, disable_setup_panel
from src.utils.branding import BOT_NAME
from src.utils.embed_style import (
    add_box_field,
    info_embed,
    style_embed,
)
from src.utils.supabase_cog import SupabaseCog

logger = logging.getLogger(__name__)

# ---------- Centralized Unicode-aware font management ----------

# ---------- Өнгөний палитр ----------
EMBED_COLOR   = 0x1e1e2f
SUCCESS_COLOR = 0x57f287
ERROR_COLOR   = 0xff0000
WARNING_COLOR = 0xfee75c
GOLD_COLOR    = 0xfab387
INFO_COLOR    = 0x89b4fa
NEON_GREEN    = (57, 255, 20, 255)
NEON_YELLOW   = (204, 255, 0, 255)

# Анхны үлдэгдэл schema-ийн default-аас авна
# (000_aether_complete.sql: economy.balance DEFAULT 1000). Энд давхар
# тогтоох нь үнэлгээнд өөр дүн үүсгэхэд ангидмаар тул зөвхөн
# лавлах хэвээр байна.
STARTING_BALANCE = 1000
DAILY_MIN = 4000
DAILY_MAX = 15000

# ---------- Татварын систем ----------
TAX_PERCENT = 10  # нийт систем дэх татварын хувь
TAX_COLLECTOR_ROLES = ("Ерөнхийлөгч", "Захирал")  # татварын орлого очих ролууд

# ---------- Балансын динамик роль ----------
WEALTH_ROLES = [
    ("Тэрбумтан", 100_000_000, 0xf1c40f),
    ("Саятан",    10_000_000, 0x9b59b6),
    ("Дундаж",     100_000,   0x3498db),
    ("Ядуу",       0,         0x95a5a6),
]

# ---------- Ажлын түвшин (цалин өссөн) ----------
JOB_LEVELS = {
    1:   {"name":"Гудамжны цас цэвэрлэгч",           "min":1800,"max":5000,"emoji":"❄️"},
    3:   {"name":"Хүнсний дэлгүүрийн ажилтан",        "min":2200,"max":5600,"emoji":"🛍️"},
    5:   {"name":"Нарантуул дээр тэрэгчин",           "min":2600,"max":7000,"emoji":"🛒"},
    8:   {"name":"Таксины жолооч",                    "min":3000,"max":7800,"emoji":"🚕"},
    10:  {"name":"CU / GS25-ын кассчин",              "min":3400,"max":7600,"emoji":"🏪"},
    12:  {"name":"Барилгын ажилтан",                  "min":4200,"max":8600,"emoji":"🧱"},
    15:  {"name":"Хүргэлтийн курьер (Пицца)",         "min":3400,"max":7000,"emoji":"🍕"},
    18:  {"name":"Бариста (Кофе шэй)",                "min":4000,"max":8000,"emoji":"☕"},
    20:  {"name":"Фитнессийн зааварлагч",             "min":4700,"max":7400,"emoji":"💪"},
    25:  {"name":"Компьютер форматлагч",              "min":5000,"max":9200,"emoji":"💻"},
    30:  {"name":"График дизайнер (Freelancer)",       "min":5400,"max":7600,"emoji":"🎨"},
    35:  {"name":"Сургуулийн багш",                   "min":6000,"max":10000,"emoji":"📚"},
    40:  {"name":"Сошиал контент бүтээгч",            "min":6000,"max":9500,"emoji":"📱"},
    45:  {"name":"Эмнэлгийн сувилагч",                "min":6600,"max":11200,"emoji":"🏥"},
    50:  {"name":"Маркетингийн менежер",              "min":7000,"max":9500,"emoji":"📊"},
    55:  {"name":"Дуучин / Хөгжимчин",                "min":8000,"max":13000,"emoji":"🎤"},
    60:  {"name":"Төслийн удирдагч",                  "min":8000,"max":10500,"emoji":"📋"},
    65:  {"name":"Хууль эрх зүйч",                    "min":8600,"max":14200,"emoji":"⚖️"},
    70:  {"name":"Кибер аюулгүй байдлын мэргэжилтэн",  "min":5600,"max":13000,"emoji":"🔒"},
    75:  {"name":"Архитектор",                        "min":8400,"max":15000,"emoji":"📐"},
    80:  {"name":"Ахлах Программист",                 "min":7800,"max":14500,"emoji":"⌨️"},
    85:  {"name":"Нефть-химийн инженер",               "min":10000,"max":17500,"emoji":"🛢️"},
    90:  {"name":"Алтны уурхайн инженер",              "min":5100,"max":16000,"emoji":"⛏️"},
    95:  {"name":"Супер модел",                       "min":11500,"max":20000,"emoji":"👗"},
    100: {"name":"Хувийн бизнес эрхлэгч",             "min":13500,"max":17000,"emoji":"🏢"},
    110: {"name":"Хөрөнгийн биржийн брокер",           "min":7500,"max":18500,"emoji":"📈"},
    120: {"name":"Томоохон банкны захирал",           "min":14000,"max":20000,"emoji":"🏦"},
    130: {"name":"Крипто трейдер",                    "min":11500,"max":23000,"emoji":"🪙"},
    140: {"name":"Олон улсын нисгэгч",                "min":9500,"max":19000,"emoji":"✈️"},
    150: {"name":"Клуб эзэмшигч",                     "min":15000,"max":25000,"emoji":"🎰"},
    160: {"name":"Тэрбумтан хөрөнгө оруулагч",        "min":11000,"max":21000,"emoji":"💼"},
    170: {"name":"Остров эзэмшигч",                   "min":17000,"max":27000,"emoji":"🏝️"},
    180: {"name":"Сансрын нисгэгч",                    "min":10000,"max":24000,"emoji":"🚀"},
    190: {"name":"Мультимиллиардер инвестор",          "min":20000,"max":33000,"emoji":"💹"},
    200: {"name":"Дэлхийн Эзэн",                     "min":10000,"max":30000,"emoji":"🌍"},
}

# ---------- Гэмт хэрэг ----------
CRIMES = [
    {"name":"Банкны ATM дээрэмдэх","success_chance":0.45,"min_reward":5000,"max_reward":15000},
    {"name":"Машин хулгайлах","success_chance":0.35,"min_reward":8000,"max_reward":20000},
    {"name":"Хүн дээрэмдэх","success_chance":0.55,"min_reward":2000,"max_reward":8000},
    {"name":"Дэлгүүр тонож байна","success_chance":0.50,"min_reward":4000,"max_reward":12000},
    {"name":"Хакердах","success_chance":0.25,"min_reward":10000,"max_reward":25000},
    {"name":"Гэмт бүлэгт элсэх","success_chance":0.15,"min_reward":1500,"max_reward":5000},
]

# /crime-ийн хүлээлт. Өмнө хүлээлтгүй байсан тул мөнгөний эх үүсвэр
# хязгааргүй байв. /work-ийн хүлээлттэй ижил.
CRIME_COOLDOWN = 1800

def _fmt_money(n: int) -> str:
    if n >= 1_000_000_000: return f"{n/1_000_000_000:.1f}B ₮"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M ₮"
    return f"{n:,} ₮"

# Per-user balance locks currently held by this task.  Used by
# Economy._balance_guard so a member who is both payer and tax collector
# does not deadlock on a non-re-entrant asyncio.Lock.
_held_balance_locks: ContextVar[frozenset[str]] = ContextVar(
    "held_balance_locks", default=frozenset()
)


# ================== MAIN ECONOMY COG ==================
class Economy(SupabaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot
        self.max_balance = bot.config.get("max_balance", 100_000_000)
        self.transfer_tax_percent = bot.config.get("tax_percent", bot.config.get("transfer_tax_percent", TAX_PERCENT))
        self.bonus_percent = bot.config.get("bonus_percent", 10)
        self.chat_money_cooldown = {}
        self.use_default_replies = True
        self._tax_collected = {}      # guild_id -> session нийт татвар
        self._tax_distributed = {}    # guild_id -> session нийт хуваарилсан
        self._collector_role_names = tuple(
            bot.config.get("tax_collector_roles", TAX_COLLECTOR_ROLES)
        )
        self._wealth_task = None
        # Per-user locks serializing balance read-modify-writes so two
        # concurrent +delta operations (e.g. work + a role income tick)
        # can never overwrite each other's update (lost update).
        # Weak values: a lock only has to outlive the critical section that
        # holds it, so an idle member's lock is reclaimed instead of the pool
        # growing for every (user, guild) pair ever seen.
        self._balance_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = (
            weakref.WeakValueDictionary()
        )
        # Serializes the /work claim for each user (double-claim guard).
        self._work_locks = {}
        # 30s per-guild cache of the active tax mode (rate, active, enabled) so
        # the hot path (every positive balance change) avoids a DB read.
        self._tax_mode_cache = {}
        # Last-payment timestamp per "guild:role" for role-income interval gating.
        self._role_income_last = {}
        self._prison_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()
        self._prison_work_last = {}

    async def _get_user_lock(self, pool: dict, key):
        lock = pool.get(key)
        if lock is None:
            lock = asyncio.Lock()
            pool[key] = lock
        return lock

    @asynccontextmanager
    async def _balance_guard(self, uid, gid):
        """Per-user balance lock that is safe to re-enter.

        The same member can be both the payer and a tax collector: paying a
        positive delta holds this member's lock while the tax distribution
        credits the collector. A plain asyncio.Lock is not re-entrant, so
        taking it twice in one call chain would deadlock the task.

        The held keys live in a ContextVar, so each task tracks its own set
        and unrelated tasks still serialise on the same member.
        """
        key = f"{uid}:{gid}"
        held = _held_balance_locks.get()
        if key in held:
            yield
            return
        lock = await self._get_user_lock(self._balance_locks, key)
        token = _held_balance_locks.set(held | {key})
        try:
            async with lock:
                yield
        finally:
            _held_balance_locks.reset(token)

    async def cog_load(self):
        # Tables are pre-configured in Supabase
        self.role_income_task = self.bot.loop.create_task(self._role_income_loop())
        self._wealth_task = self.bot.loop.create_task(self._wealth_role_loop())

    async def cog_unload(self):
        """Docs extension-teardown best practice: cancel background tasks."""
        for task in (self.role_income_task, self._wealth_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def ensure_user(self, uid, gid):
        row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)})
        if not row:
            await self.update_data("economy", {"user_id": str(uid), "guild_id": str(gid)})

    # ── Persistent command cooldowns ────────────────────────────────
    # These used to live in process memory, so restarting the bot re-armed
    # every money faucet and rate limit.  They are stored on the economy row
    # next to last_daily / last_work (migration 008).
    COOLDOWN_COLUMNS = ("last_crime", "last_rob", "last_hack", "last_give")

    async def _get_work_money_mult(self, guild_id, user_id) -> int:
        """Return the cafe work multiplier as a percent (100 = no buff).

        The cafe buff stores ``money_mult``; it was written by the cafe,
        carts and shop cogs but never read, so a purchased "Lightning Soda"
        doubled nothing.  Returns 100 when no buff applies.
        """
        try:
            cafe = self.bot.get_cog("Cafe")
            if cafe is None or not hasattr(cafe, "get_buff"):
                return 100
            buff = cafe.get_buff(user_id, guild_id)
            if asyncio.iscoroutine(buff):
                buff = await buff
            if not buff or buff.get("type") != "work_mult":
                return 100
            mult = float(buff.get("money_mult") or 1)
            if mult <= 0:
                return 100
            return max(1, int(mult * 100))
        except Exception:
            logger.exception("Operation failed in _get_work_money_mult")
            return 100

    async def get_command_cooldown(self, uid, gid, column, limit):
        """Return the remaining cooldown in seconds; 0 when the command is ready."""
        if column not in self.COOLDOWN_COLUMNS:
            raise ValueError(f"unknown cooldown column: {column}")
        row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)})
        last = (row or {}).get(column) or 0
        now = time.time()
        if now - last < limit:
            return int(limit - (now - last))
        return 0

    async def set_command_cooldown(self, uid, gid, column):
        """Stamp the command as used now so the next call is rate limited."""
        if column not in self.COOLDOWN_COLUMNS:
            raise ValueError(f"unknown cooldown column: {column}")
        await self.ensure_user(uid, gid)
        await self.bot.db_manager.update(
            "economy",
            {"user_id": str(uid), "guild_id": str(gid)},
            {column: int(time.time())},
        )

    async def get_balance(self, uid, gid):
        row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)})
        return row.get("balance", 0) if row else 0

    async def update_balance(
        self, uid, gid, delta, apply_tax: bool | None = None, *, reference: str | None = None
    ):
        """Гар дээрх үлдэгдэл өөрчлөх. Эерэг орлогод татвар автан
        (Government system идэвхтэй бол түүний хүлээн авагчдад, эс бөгөөс
        Ерөнхийлөгч/Захирал ролттой хэрэглэгчид) автоматаар хуваарилагдана.
        Татварын өөрөө хуваарилах үедээ apply_tax=False дамжуулна.

        ``reference`` өгсөн үед Supabase RPC нь balance update, reference
        claim, татварын бүх balance/treasury шилжүүлгийг нэг transaction-д
        хийж, retry/давхар дуудлагыг нэг л удаа хэрэгжүүлнэ. Ижил reference
        өөр дүн/татвартай дахин ашиглагдвал DB алдаа өгнө.
        """
        if reference is not None:
            reference = str(reference).strip()
            if not reference or len(reference) > 200:
                raise ValueError("reference must contain 1-200 characters")

        tax = 0
        credited = delta
        result = None
        async with self._balance_guard(uid, gid):
            if reference is None:
                await self.ensure_user(uid, gid)
            if delta > 0 and (apply_tax if apply_tax is not None else True):
                rate = await self.get_effective_rate(gid)
                # rate нь бүхэл тоо тул бүхэл хуваарь ашиглана.
                # int(delta * rate / 100) нь float алдаанаас улмаас
                # үргэлж доош тасардаг.
                tax = delta * rate // 100
                credited = delta - tax
            else:
                tax = 0
                credited = delta

            if reference is not None:
                plan = await self._prepare_reference_tax_plan(gid, tax)
                try:
                    response = await self.bot.db_manager.rpc(
                        "apply_economy_balance_with_tax_once",
                        {
                            "p_reference": reference,
                            "p_user_id": str(uid),
                            "p_guild_id": str(gid),
                            "p_delta": int(credited),
                            "p_max_balance": int(self.max_balance),
                            "p_tax": tax,
                            "p_credits": plan["credits"],
                            "p_treasury": plan["treasury"],
                            "p_discarded": plan["discarded"],
                        },
                    )
                except DatabaseSchemaError as exc:
                    raise RuntimeError(
                        "Economy-ийн atomic balance migration дутуу байна (migration 005)."
                    ) from exc
                except InsufficientFundsError:
                    raise
                except Exception as exc:
                    # The RPC enforces balance >= 0 atomically and raises
                    # "insufficient balance ...". Surface it as the typed error so
                    # every caller handles both paths identically.
                    if "insufficient balance" in str(exc).lower():
                        raise InsufficientFundsError(
                            f"insufficient balance for user {uid} in guild {gid}"
                        ) from exc
                    raise
                data = getattr(response, "data", response)
                if isinstance(data, list):
                    row = data[0] if data else None
                elif isinstance(data, dict):
                    row = data
                else:
                    row = None
                if not row or "balance" not in row or type(row.get("applied")) is not bool:
                    raise RuntimeError("apply_economy_balance_with_tax_once returned an invalid response")
                balance = int(row["balance"])
                if row["applied"] and tax > 0:
                    self._tax_collected[gid] = self._tax_collected.get(gid, 0) + tax
                    shipped = sum(credit["amount"] for credit in plan["credits"])
                    self._tax_distributed[gid] = self._tax_distributed.get(gid, 0) + shipped
                    gov = self.bot.get_cog("Government")
                    if gov is not None:
                        gov._settings_cache.pop(str(gid), None)
                result = balance
            else:
                cur = await self.get_balance(uid, gid)
                new = cur + credited
                if new < 0:
                    # Balance must never go negative. Silently clamping to 0 would
                    # let a caller commit a bet larger than the balance it holds
                    # while still paying out on the full stake, so refuse instead.
                    raise InsufficientFundsError(
                        f"insufficient balance for user {uid} in guild {gid}: "
                        f"current {cur} + delta {credited} would go below 0"
                    )
                new = min(new, self.max_balance)
                await self.update_data("economy", {"user_id": str(uid), "guild_id": str(gid), "balance": new})
                result = new

        # Татварын хуваарилалтыг түлхүүрийн lock-ийн гадна хийнэ: хүлээн
        # авагчийн өөрийн lock-ыг авах шаардлагатай бөгөөд хоёр хэрэглэгчийн
        # lock-ыг зэрэг авбал deadlock болно. Зорилтот balance амжилттай
        # бичигдсэн дараа хуваарилах тул амжилтгүй бичлэг дээр мөнгө үүсэхгүй.
        if tax > 0 and reference is None:
            try:
                await self.distribute_tax(gid, tax)
            except Exception as exc:
                # Татварын зорилтот balance амжилттай бичигдсэн тул татвар
                # алгасах нь мөнгө үүсгэхээс хамааргүй. Хэрэглэгчид
                # "төлбөр шилжээд амжилтанд хүрээгүй" гэж харагдахыг хоригно.
                logger.warning("tax distribution failed gid=%s: %s", gid, exc, exc_info=True)
        return result

    async def _prepare_reference_tax_plan(self, gid, tax: int) -> dict:
        """Snapshot live recipients before the atomic RPC; never mutate money."""
        plan = None
        if tax > 0:
            gov = self.bot.get_cog("Government")
            if gov is not None:
                plan = await gov.prepare_tax_plan(gid, tax)
        if plan is None:
            collectors = await self.get_tax_collectors(gid) if tax > 0 else []
            share = tax // len(collectors) if collectors else 0
            remainder = tax - share * len(collectors)
            plan = {
                "credits": [(member.id, share + (remainder if index == 0 else 0), "")
                            for index, member in enumerate(collectors)],
                "treasury": 0, "tax": tax, "discarded": 0 if collectors else tax,
            }
        treasury, discarded = plan.get("treasury"), plan.get("discarded", 0)
        if (
            plan.get("tax") != tax or type(treasury) is not int or treasury < 0
            or type(discarded) is not int or discarded < 0
        ):
            raise ValueError("Invalid tax distribution plan")
        credits = []
        seen = set()
        for uid, amount, _label in plan.get("credits", []):
            user_id = str(uid)
            if (
                not user_id.isascii() or not user_id.isdigit() or int(user_id) <= 0
                or type(amount) is not int or amount < 0 or user_id in seen
            ):
                raise ValueError("Invalid tax recipient")
            seen.add(user_id)
            if amount:
                credits.append({"user_id": user_id, "amount": amount})
        if sum(credit["amount"] for credit in credits) + treasury + discarded != tax:
            raise ValueError("Tax distribution total does not match collected tax")
        return {"credits": sorted(credits, key=lambda credit: credit["user_id"]),
                "treasury": treasury, "discarded": discarded}

    async def get_tax_collectors(self, gid):
        """Ерөнхийлөгч / Захирал рольтой гишүүдийг олох."""
        guild = self.bot.get_guild(int(gid))
        if not guild:
            return []
        collectors = []
        for role_name in self._collector_role_names:
            role = discord.utils.find(
                lambda r, expected=role_name: r.name.lower() == expected.lower(),
                guild.roles,
            )
            if role:
                collectors.extend(m for m in role.members if not m.bot)
        # Давхардлыг арилгах
        seen = set()
        unique = []
        for m in collectors:
            if m.id not in seen:
                seen.add(m.id)
                unique.append(m)
        return unique

    def invalidate_tax_cache(self, gid):
        self._tax_mode_cache.pop(str(gid), None)

    async def get_tax_mode(self, gid):
        """Return (rate, active, enabled) for the guild's tax.

        When the Government system is active for the guild, the configured
        government tax rate + enabled flag wins (30s cache). Otherwise the
        legacy ``transfer_tax_percent`` applies and ``active`` is False so the
        legacy collector-role path stays untouched.
        """
        key = str(gid)
        now = time.monotonic()
        cached = self._tax_mode_cache.get(key)
        if cached and now - cached[0] < 30:
            return cached[1]
        mode = None
        gov = self.bot.get_cog("Government")
        if gov is not None and hasattr(gov, "government_tax"):
            try:
                res = await gov.government_tax(gid)
                if res is not None:
                    mode = (int(res[0]), True, bool(res[1]))
            except Exception as e:
                logger.warning("government_tax failed gid=%s: %s", gid, e, exc_info=True)
        if mode is None:
            mode = (self.transfer_tax_percent, False, True)
        self._tax_mode_cache[key] = (now, mode)
        return mode

    async def get_effective_rate(self, gid) -> int:
        rate, _active, enabled = await self.get_tax_mode(gid)
        return rate if enabled else 0

    async def distribute_tax(self, gid, tax: int):
        """Цугларсан татварыг хуваарилах.

        Government system идэвхтэй бол Government cog-ийн тохируулсан
        хүлээн авагчдад хуваарилагдана. Идэвхгүй бол легаси зан үйл:
        Ерөнхийлөгч/Захирал ролт хэрэглэгчид. Татвар цуглуулагч байхгүй бол
        орлого алдагдана (сан хөрөнгө)."""
        self._tax_collected[gid] = self._tax_collected.get(gid, 0) + tax
        gov = self.bot.get_cog("Government")
        if gov is not None and hasattr(gov, "distribute_tax") and hasattr(gov, "is_government_active"):
            try:
                if await gov.is_government_active(gid):
                    shipped = await gov.distribute_tax(gid, tax)
                    self._tax_distributed[gid] = self._tax_distributed.get(gid, 0) + shipped
                    return shipped
            except Exception as e:
                logger.warning("government distribute_tax failed gid=%s: %s", gid, e, exc_info=True)
                # A failed distribution may already have credited recipients.
                # Switching to legacy collectors here would distribute twice.
                raise
        collectors = await self.get_tax_collectors(gid)
        if not collectors or tax <= 0:
            return 0
        share = tax // len(collectors)
        remainder = tax - share * len(collectors)
        distributed = 0
        for i, member in enumerate(collectors):
            amount = share + (remainder if i == 0 else 0)
            if amount <= 0:
                continue
            # Хүлээн авагчийн туслас balance lock-оор хамгаалагдана.
            # Өмнө нь lock-гүй read-modify-write байсан тул хүлээн авагчийн
            # зэрэгцээ олсон орлого дүүрэгдэх боломжтой байлаа.
            async with self._balance_guard(member.id, gid):
                await self.ensure_user(member.id, gid)
                row = await self.get_data("economy", {"user_id": str(member.id), "guild_id": str(gid)}) or {}
                cur = int(row.get("balance") or 0)
                new = min(self.max_balance, cur + amount)
                await self.update_data("economy", {"user_id": str(member.id), "guild_id": str(gid), "balance": new})
                distributed += amount
        self._tax_distributed[gid] = self._tax_distributed.get(gid, 0) + distributed
        return distributed

    @staticmethod
    def _is_missing_rpc(exc: Exception) -> bool:
        """True when the failure means the SQL function is not installed yet."""
        code = str(getattr(exc, "code", "") or "")
        text = str(exc).lower()
        return (
            code in ("PGRST202", "404", "42883")
            or "does not exist" in text
            or "could not find the function" in text
        )

    async def _transfer_principal(self, sender_id, gid, receiver_id, amount, tax, reference):
        """Move `amount` from the sender to the receiver atomically.

        Uses apply_economy_transfer_once() (migration 009) when it is
        available. The transfer tax is distributed to the collectors in the
        same transaction, so a crash cannot leave the amount half-moved.
        When the RPC is not available the caller falls back to the locked
        two-write path, which is still safe within this process.

        Returns (sender_after, receiver_after), or None when the RPC could
        not be used.
        """
        plan = await self._prepare_reference_tax_plan(gid, tax)
        try:
            response = await self.bot.db_manager.rpc(
                "apply_economy_transfer_once",
                {
                    "p_reference": reference,
                    "p_from_user_id": str(sender_id),
                    "p_from_guild_id": str(gid),
                    "p_to_user_id": str(receiver_id),
                    "p_to_guild_id": str(gid),
                    "p_amount": int(amount),
                    "p_max_balance": int(self.max_balance),
                    "p_tax": int(tax),
                    "p_credits": plan["credits"],
                    "p_treasury": plan["treasury"],
                    "p_discarded": plan["discarded"],
                },
            )
        except Exception as exc:
            if self._is_missing_rpc(exc):
                logger.info(
                    "transfer RPC unavailable (apply migration 009); using the locked path",
                    exc_info=True,
                )
            else:
                logger.warning("atomic transfer RPC failed: %s", exc, exc_info=True)
            return None
        data = getattr(response, "data", response)
        if isinstance(data, list):
            row = data[0] if data else None
        elif isinstance(data, dict):
            row = data
        else:
            row = None
        if not row or "from_balance" not in row or "to_balance" not in row:
            logger.warning("atomic transfer RPC returned an invalid response")
            return None
        if tax > 0 and row.get("applied"):
            self._tax_collected[gid] = self._tax_collected.get(gid, 0) + tax
            self._tax_distributed[gid] = self._tax_distributed.get(gid, 0) + int(
                row.get("tax_shipped") or 0
            )
        return int(row["from_balance"]), int(row["to_balance"])

    async def get_bank(self, uid, gid):
        row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)})
        return row.get("bank_balance", 0) if row else 0

    async def update_bank(self, uid, gid, delta):
        """Change a member's bank balance.

        The read-modify-write runs under the same per-user guard as
        move_cash_and_bank, so a concurrent cash/bank move cannot be lost.
        An overdraft is refused instead of being silently clamped to zero:
        clamping let a caller debit more than the bank held and still pay
        out on the full amount.
        """
        async with self._balance_guard(uid, gid):
            await self.ensure_user(uid, gid)
            row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)}) or {}
            cur = int(row.get("bank_balance") or 0)
            new = cur + delta
            if new < 0:
                raise InsufficientFundsError(
                    f"insufficient bank balance for user {uid} in guild {gid}: "
                    f"current {cur} + delta {delta} would go below 0"
                )
            if new > self.max_balance:
                raise ValueError("bank balance cap exceeded")
            await self.update_data("economy", {"user_id": str(uid), "guild_id": str(gid), "bank_balance": new})
            return new

    async def move_cash_and_bank(self, uid, gid, amount: int, *, to_bank: bool):
        """Atomically move funds between one member's cash and bank balances."""
        async with self._balance_guard(uid, gid):
            await self.ensure_user(uid, gid)
            row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)}) or {}
            cash, bank = int(row.get("balance") or 0), int(row.get("bank_balance") or 0)
            source, target = (cash, bank) if to_bank else (bank, cash)
            if amount <= 0 or source < amount or target + amount > self.max_balance:
                raise ValueError("Invalid internal money transfer")
            cash, bank = (cash - amount, bank + amount) if to_bank else (cash + amount, bank - amount)
            await self.update_data(
                "economy",
                {
                    "user_id": str(uid), "guild_id": str(gid),
                    "balance": cash, "bank_balance": bank,
                },
            )
            return cash, bank

    async def record_money(self, gid, uid, actor_id, transaction_type, amount,
                           balance_before=None, balance_after=None, reason=None, metadata=None):
        """Best-effort immutable money audit; a log failure never breaks payment."""
        try:
            await self.bot.db_manager.insert("economy_ledger", {
                "guild_id": str(gid), "user_id": str(uid) if uid is not None else None,
                "actor_id": str(actor_id) if actor_id is not None else None,
                "transaction_type": transaction_type, "amount": int(amount),
                "balance_before": balance_before, "balance_after": balance_after,
                "reason": reason, "metadata": metadata, "created_at": int(time.time()),
            })
        except Exception as exc:
            logger.warning("economy ledger write failed: %s", exc, exc_info=True)

    @commands.hybrid_command(name="transactions", aliases=["tx", "history"])
    async def transactions(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        if target.id != ctx.author.id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=discord.Embed(title="⛔ Эрх хүрэхгүй", description="Бусдын гүйлгээг зөвхөн Manage Server эрхтэй хүн харна.", color=ERROR_COLOR))
        rows = await self.bot.db_manager.fetch_all(
            "economy_ledger", {"guild_id": str(ctx.guild.id), "user_id": str(target.id)},
            order_by="created_at", desc=True, limit=10,
        )
        if not rows:
            return await ctx.send(embed=info_embed("Гүйлгээний түүх", "Одоогоор бүртгэл алга."))
        labels = {"work": "💼 Ажил", "daily": "🎁 Daily", "transfer_out": "📤 Шилжүүлсэн",
                  "transfer_in": "📥 Хүлээн авсан", "deposit": "🏦 Хадгалсан", "withdraw": "💵 Татан авсан"}
        lines = []
        for row in rows:
            amount = int(row.get("amount") or 0)
            sign = "+" if amount > 0 else ""
            when = f"<t:{int(row.get('created_at') or 0)}:R>"
            lines.append(f"{labels.get(row.get('transaction_type'), '💠 Гүйлгээ')} • **{sign}{amount:,} ₮** • {when}")
        embed = discord.Embed(title=f"💳 {target.display_name} — Сүүлийн гүйлгээ", description="\n".join(lines), color=GOLD_COLOR)
        await ctx.send(embed=embed)

    async def get_top_balances(self, guild_id: int, limit=10, offset=0):
        """Хамгийн их үлдэгдэлтэй хэрэглэгчид (Leaderboard ког ашиглах)."""
        rows = await self.bot.db_manager.fetch_all(
            "economy", {"guild_id": str(guild_id)},
            order_by="balance", desc=True, limit=limit, offset=offset,
        )
        return [(int(r["user_id"]), r.get("balance", 0) or 0) for r in rows]

    # ------- USER MANAGEMENT -------
    async def check_registration(self, ctx):
        await self.ensure_user(ctx.author.id, ctx.guild.id)
        return True

    # ------- HUNGER / MOOD -------
    async def get_hunger_mood(self, uid, gid):
        row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)})
        return (row.get("hunger", 0), row.get("mood", 0)) if row else (0, 0)

    async def set_hunger_mood(self, uid, gid, hunger=None, mood=None):
        updates = {}
        if hunger is not None:
            updates["hunger"] = max(0, min(100, hunger))
        if mood is not None:
            updates["mood"] = max(0, min(100, mood))
        if updates:
            await self.bot.db_manager.update(
                "economy", {"user_id": str(uid), "guild_id": str(gid)}, updates
            )

    # ------- LEVEL / JOB -------
    async def get_discord_level(self, uid, gid):
        level_cog = self.bot.get_cog("Leveling")
        if level_cog:
            row = await self.get_data("levels", {"user_id": str(uid), "guild_id": str(gid)})
            if row:
                return row.get("level", 1)
        return 1

    def get_job_for_level(self, lvl):
        for req in sorted(JOB_LEVELS.keys(), reverse=True):
            if lvl >= req:
                return req, JOB_LEVELS[req]
        return 1, JOB_LEVELS[1]

    # ------- PRISON / BANK PROTECTION -------
    async def is_in_prison(self, uid, gid):
        row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)})
        return row and row.get("prison_until") and row["prison_until"] > int(time.time())

    async def get_prison_remaining(self, uid, gid):
        row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)})
        until = int(row.get("prison_until") or 0) if row else 0
        return max(0, until - int(time.time()))

    async def set_prison(self, uid, gid, hours=2):
        until = int(time.time()) + (hours * 3600)
        await self.bot.db_manager.update(
            "economy", {"user_id": str(uid), "guild_id": str(gid)}, {"prison_until": until}
        )

    async def set_bank_protection(self, uid, gid, hours=2):
        until = int(time.time()) + (hours * 3600)
        await self.bot.db_manager.update(
            "economy", {"user_id": str(uid), "guild_id": str(gid)}, {"bank_protect_until": until}
        )

    async def get_bank_protection_remaining(self, uid, gid):
        row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)})
        if row and row.get("bank_protect_until") and row["bank_protect_until"] > int(time.time()):
            return row["bank_protect_until"] - int(time.time())
        return 0

    async def is_bank_protected(self, uid, gid):
        return await self.get_bank_protection_remaining(uid, gid) > 0

    # ------- ADMIN CONFIG SETTERS -------
    async def set_cooldown_cmd(self, interaction, command, seconds):
        await self.bot.db_manager.upsert(
            "economy_cooldowns_config",
            {"guild_id": str(interaction.guild_id), "command": command, "cooldown_seconds": seconds},
            on_conflict="guild_id,command",
        )

    async def set_fine_amount(self, interaction, command, mn, mx):
        await self.bot.db_manager.upsert(
            "economy_fines_config",
            {"guild_id": str(interaction.guild_id), "command": command, "fine_min": mn, "fine_max": mx},
            on_conflict="guild_id,command",
        )

    async def set_payout(self, interaction, command, mn, mx):
        await self.bot.db_manager.upsert(
            "economy_payouts_config",
            {"guild_id": str(interaction.guild_id), "command": command, "payout_min": mn, "payout_max": mx},
            on_conflict="guild_id,command",
        )

    async def set_fail_rate(self, interaction, command, rate):
        await self.bot.db_manager.upsert(
            "economy_fail_rates",
            {"guild_id": str(interaction.guild_id), "command": command, "fail_rate": rate},
            on_conflict="guild_id,command",
        )

    async def add_reply(self, interaction, command, text, rtype):
        await self.bot.db_manager.insert(
            "custom_replies",
            {"guild_id": str(interaction.guild_id), "command": command, "type": rtype, "text": text},
        )

    # ================== COMMANDS ==================
    @commands.hybrid_command(name='admin-panel')
    @commands.has_permissions(administrator=True)
    async def admin_panel(self, ctx):
        view = AdminPanelView(self, ctx)
        embed = (
            SetupPanel(
                "Economy command дүрэм",
                "Команд тус бүрийн cooldown, мөнгөн дүн болон хариуг тохируулна.",
                icon="🛠️",
                state=SetupState.READY,
                status="Админ тохиргоо идэвхтэй",
            )
            .section("Тохируулж болох зүйл", [
                "⏱️ **Cooldown** — дахин ашиглах хүртэлх хугацаа",
                "💸 **Торгууль** — алдахад хасагдах min/max дүн",
                "💰 **Цалин** — амжилтад авах min/max дүн",
                "🎲 **Бүтэлгүйтэх хувь** — 0–100% магадлал",
                "💬 **Custom reply** — success/fail хариу",
            ], icon="⚙️")
            .finish("Самбар 3 минут идэвхтэй", actor=ctx.author)
        )
        view.message = await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name='workphrase', description='Ажлын өгүүлбэрийн тохиргоо (embed+button+modal)')
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def work_phrase_panel(self, ctx):
        rows = await self.bot.db_manager.fetch_all(
            "work_phrases", {"guild_id": str(ctx.guild.id)}, selects="id"
        )
        embed = (
            SetupPanel(
                "Ажлын өгүүлбэр",
                "`work` командын санамсаргүй өгүүлбэрүүдийг удирдана.",
                icon="📝",
                state=SetupState.READY if rows else SetupState.INCOMPLETE,
                status=f"{len(rows)} өгүүлбэр бүртгэлтэй",
                color=GOLD_COLOR,
            )
            .section("Үйлдэл", [
                "➕ Шинэ өгүүлбэр нэмэх",
                "➖ ID-аар нэг өгүүлбэр хасах",
                "📋 Одоогийн жагсаалтыг харах",
                "🧹 Бүх өгүүлбэрийг цэвэрлэх",
            ], icon="⚙️")
            .finish("Самбар 5 минут идэвхтэй", actor=ctx.author)
        )
        view = WorkPhraseView(self, ctx)
        view.message = await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(aliases=['bal','money','wallet','bank'])
    async def balance(self, ctx, member: discord.Member = None):
        if ctx.guild is None:
            return await ctx.send("❌ Энэ командыг зөвхөн серверт ашиглаж болно.")
        if not await self.check_registration(ctx): return
        target = member or ctx.author
        cash = await self.get_balance(target.id, ctx.guild.id)
        bank = await self.get_bank(target.id, ctx.guild.id)
        total = cash + bank
        disc_level = await self.get_discord_level(target.id, ctx.guild.id)
        job_level, job = self.get_job_for_level(disc_level)
        color = 0xffd700 if total >= 50000 else EMBED_COLOR
        embed = style_embed(f"{target.display_name} - САНХҮҮ", "", color, "bank")
        embed.set_thumbnail(url=target.display_avatar.url)
        add_box_field(embed, "ҮЛДЭГДЭЛ", [
            f"╭ Гар дээр\n╰→ {cash:,} ₮",
            f"╭ Банканд\n╰→ {bank:,} ₮",
            f"╭ Нийт хөрөнгө\n╰→ {total:,} ₮",
        ])
        add_box_field(embed, "АЖИЛ БА ТҮВШИН", [
            f"╭ Ажил\n╰→ {job['emoji']} {job['name']} (Түв.{job_level})",
            f"╭ Discord түвшин\n╰→ {disc_level}",
        ])
        embed.set_footer(text=f"{BOT_NAME} • {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='work')
    async def work(self, ctx, *, custom_text: str | None = None):
        if not await self.check_registration(ctx): return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send(embed=discord.Embed(title="🚔 Шорон", description="Та шоронгоос ажиллах боломжгүй.", color=ERROR_COLOR))
        hunger, mood = await self.get_hunger_mood(ctx.author.id, ctx.guild.id)
        if hunger >= 80:
            return await ctx.send(embed=discord.Embed(title="🍔 Өлсөж байна!", description="`eat` командаар хоол идээрэй.", color=WARNING_COLOR))
        if mood >= 80:
            return await ctx.send(embed=discord.Embed(title="😡 Ууртай байна!", description="`relax` командаар амраарай.", color=WARNING_COLOR))

        # Double-claim guard: the cooldown check + `last_work` write must be
        # atomic per user so two rapid /work invocations pay only once.
        work_lock = await self._get_user_lock(self._work_locks, f"{ctx.author.id}:{ctx.guild.id}")
        async with work_lock:
            now = int(time.time())
            row = await self.bot.db_manager.fetch_one("economy", {"user_id": str(ctx.author.id), "guild_id": str(ctx.guild.id)}, selects="last_work")
            last = row.get("last_work", 0) if row else 0
            if last and now - last < 1800:
                rem = 1800 - (now-last)
                m, s = divmod(rem, 60)
                return await ctx.send(embed=discord.Embed(title="⏳ АМРАЛТ", description=f"**{m}м {s}с** хүлээ.", color=WARNING_COLOR))

            disc_level = await self.get_discord_level(ctx.author.id, ctx.guild.id)
            gov = self.bot.get_cog("Government")
            custom = None
            if gov is not None and hasattr(gov, "resolve_user_job"):
                try:
                    if await gov.is_government_active(ctx.guild.id):
                        custom = await gov.resolve_user_job(ctx.guild.id, disc_level, member=ctx.author)
                except Exception:
                    logger.exception("Operation failed in work")
                    custom = None
            if custom:
                job = {"min": custom["min"], "max": custom["max"], "emoji": custom["emoji"], "name": custom["name"]}
            else:
                _job_level, job = self.get_job_for_level(disc_level)
            pay = random.randint(job["min"], job["max"])
            bonus = min(50, disc_level * 2)
            # Бүхэл тоонд шууд тооцоолно: int(pay * (1 + bonus/100)) нь
            # float алдаанаас 1 ₮-ийн зөрүү гаргаж байлаа.
            if bonus: pay = pay + (pay * bonus) // 100
            # Cafe-ийн work_mult buff (Lightning Soda) цалингаа үржүүлнэ.
            # Өмнө нь money_mult бичигдэдэг боловч хаана ч уншигдахгүй
            # байсан тул худалдан авсан buff огт нөлөө үзүүлэхгүй байлаа.
            work_mult = await self._get_work_money_mult(ctx.guild.id, ctx.author.id)
            if work_mult != 100:
                pay = pay * work_mult // 100

            if custom_text:
                work_desc = custom_text
            else:
                rows = await self.bot.db_manager.fetch_safe(
                    "work_phrases", {"guild_id": str(ctx.guild.id)}, selects="phrase"
                )
                if rows:
                    work_desc = random.choice(rows)["phrase"]
                else:
                    work_desc = f"{job['emoji']} {job['name']} ажил"

            # Күүкийг төлбөрийн өмнө тэмдэглэнэ. Амжилтын тооцоо ба төлбөрийн
            # хооронд процесс унахад дахин өгүүлж болохгүй байх ёстой:
            # урьд нь төлбөр эхлээд өгөгдөж, хүлээлт дараа нь бичигдэж байлаа.
            await self.bot.db_manager.update("economy", {"user_id": str(ctx.author.id), "guild_id": str(ctx.guild.id)}, {"last_work": now})

            before = await self.get_balance(ctx.author.id, ctx.guild.id)
            after = await self.update_balance(ctx.author.id, ctx.guild.id, pay)
            rate = await self.get_effective_rate(ctx.guild.id)
            tax = pay * rate // 100
            hunger_inc = random.randint(10, 15)
            mood_inc = random.randint(10, 15)
            new_hunger = min(100, hunger+hunger_inc)
            new_mood = min(100, mood+mood_inc)
            await self.set_hunger_mood(ctx.author.id, ctx.guild.id, hunger=new_hunger, mood=new_mood)
            await self.record_money(ctx.guild.id, ctx.author.id, ctx.author.id, "work", after - before, before, after, job["name"])
            quests_cog = self.bot.get_cog("Quests")
            try:
                if quests_cog:
                    await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "economy_work", 1)
            except Exception as exc:
                logger.warning("work quest trigger failed: %s", exc, exc_info=True)

        tax_line = f"\n🏛️ Татвар ({rate}%): -{tax:,} ₮ (Татвар-д)" if tax > 0 else ""
        embed = discord.Embed(
            title="💼 АЖИЛ АМЖИЛТТАЙ!",
            description=f"{ctx.author.mention} **{work_desc}** хийж, **{pay:,}** ₮ оллоо!\n⭐ Урамшуулал: +{bonus}%{tax_line}",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(UTC)
        )
        embed.add_field(name="💰 Цалин", value=f"+ {pay:,} ₮", inline=True)
        embed.add_field(name="🍔 Өлсгөлөн", value=f"+{hunger_inc}% (одоо {new_hunger}/100)", inline=True)
        embed.add_field(name="😡 Уур", value=f"+{mood_inc}% (одоо {new_mood}/100)", inline=True)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Дараагийн ажил 30 минутын дараа")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='daily')
    async def daily(self, ctx):
        if not await self.check_registration(ctx): return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send(embed=discord.Embed(title="🚔 Шорон", description="Та шоронгоос урамшуулал авах боломжгүй.", color=ERROR_COLOR))
        # Double-claim guard: cooldown шалгалт + last_daily бичилтийг хэрэглэгч бүрт
        # атомар болгох — /work-той ижилхэн (давхар авахаас сэргийлнэ).
        daily_lock = await self._get_user_lock(self._work_locks, f"{ctx.author.id}:{ctx.guild.id}")
        async with daily_lock:
            now = int(time.time())
            row = await self.bot.db_manager.fetch_one("economy", {"user_id": str(ctx.author.id), "guild_id": str(ctx.guild.id)}, selects="last_daily")
            last = row.get("last_daily", 0) if row else 0
            if last and now - last < 86400:
                rem = 86400 - (now-last)
                h, m, s = rem//3600, (rem%3600)//60, rem%60
                time_left = f"{h}ч {m}м {s}с"
                return await ctx.send(embed=discord.Embed(title="⏰ Daily", description=f"Дахин авах хүртэл: **{time_left}**", color=WARNING_COLOR))
            reward = random.randint(DAILY_MIN, DAILY_MAX)
            await self.bot.db_manager.update("economy", {"user_id": str(ctx.author.id), "guild_id": str(ctx.guild.id)}, {"last_daily": now})
            before = await self.get_balance(ctx.author.id, ctx.guild.id)
            after = await self.update_balance(ctx.author.id, ctx.guild.id, reward)
            await self.record_money(ctx.guild.id, ctx.author.id, ctx.author.id, "daily", after - before, before, after, "Daily reward")
            rate = await self.get_effective_rate(ctx.guild.id)
            tax_note = f"\n🏛️ Татвар ({rate}%): -{int(reward * rate / 100):,} ₮" if reward > 0 else ""
            embed = discord.Embed(
                title="🎉 Daily Reward",
                description=f"Өдрийн шагнал: **{reward:,} ₮**",
                color=SUCCESS_COLOR,
                timestamp=datetime.now(UTC)
            )
            embed.add_field(name="💰 Шагнал", value=f"+ **{reward:,}** ₮{tax_note}")
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text="Дараагийн урамшуулал 24 цагийн дараа")
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='crime')
    async def crime(self, ctx):
        if not await self.check_registration(ctx): return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send(embed=discord.Embed(title="🚔 Шорон", description="Та шоронд гэмт хэрэг үйлдэх боломжгүй.", color=ERROR_COLOR))
        cd = await self.get_command_cooldown(ctx.author.id, ctx.guild.id, "last_crime", CRIME_COOLDOWN)
        if cd:
            m, s = divmod(cd, 60)
            return await ctx.send(embed=discord.Embed(title="⏳ КҮЛЭЭ", description=f"**{m}м {s}с** хүлээ.", color=WARNING_COLOR))
        # Күүкийг амжилтын тооцоогоос өмнө тэмдэглэнэ. Амжилтгүй болбол
        # дахин хэдэн ч удаа орж болохгүй байх ёстой.
        await self.set_command_cooldown(ctx.author.id, ctx.guild.id, "last_crime")
        crime = random.choice(CRIMES)
        if random.random() < crime["success_chance"]:
            reward = random.randint(crime["min_reward"], crime["max_reward"])
            await self.update_balance(ctx.author.id, ctx.guild.id, reward)
            rate = await self.get_effective_rate(ctx.guild.id)
            crime_tax_note = f"\n🏛️ Татвар ({rate}%): -{int(reward * rate / 100):,} ₮"
            embed = discord.Embed(title="🎉 ГЭМТ ХЭРЭГ АМЖИЛТТАЙ!",
                                  description=f"{ctx.author.mention} **{crime['name']}** үйлдэж, **{reward:,}** ₮ оллоо!{crime_tax_note}",
                                  color=SUCCESS_COLOR,
                                  timestamp=datetime.now(UTC))
            embed.add_field(name="💰 Шагнал", value=f"+ {reward:,} ₮")
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
        else:
            jail_time = random.randint(1, 3)
            await self.set_prison(ctx.author.id, ctx.guild.id, hours=jail_time)
            embed = discord.Embed(title="🚔 ТА ЦАГДААД БАРИГДЛАА!",
                                  description=f"{ctx.author.mention} **{crime['name']}** үйлдэх гэж оролдсон боловч баригдлаа! {jail_time} цаг шоронд сууна.",
                                  color=ERROR_COLOR,
                                  timestamp=datetime.now(UTC))
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='transfer', aliases=['send', 'give'])
    async def transfer(self, ctx, member: discord.Member, amount_str: str):
        if not await self.check_registration(ctx): return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send(embed=discord.Embed(title="🚔 Шорон", description="Та шоронгоос мөнгө шилжүүлэх боломжгүй.", color=ERROR_COLOR))
        if amount_str.lower() == 'all':
            amount = await self.get_balance(ctx.author.id, ctx.guild.id)
        else:
            try: amount = int(amount_str)
            except ValueError:
                return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Дүн нь тоо эсвэл 'all' байх ёстой.", color=ERROR_COLOR))
        if amount <= 0: return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Дүн эерэг байх ёстой.", color=ERROR_COLOR))
        if member.id == ctx.author.id: return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Өөртөө мөнгө шилжүүлэх боломжгүй.", color=ERROR_COLOR))
        rate = await self.get_effective_rate(ctx.guild.id)
        tax = amount * rate // 100
        final_amount = amount - tax
        if final_amount <= 0: return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Татварын дараа шилжих мөнгө 0 боллоо.", color=ERROR_COLOR))
        sender_bal = await self.get_balance(ctx.author.id, ctx.guild.id)
        if sender_bal < amount: return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description=f"Танд {amount:,} ₮ хүрэлцэхгүй.", color=ERROR_COLOR))
        embed = discord.Embed(title="💰 МӨНГӨ ШИЛЖҮҮЛЭХ",
                              description=f"{ctx.author.mention} → {member.mention}\nДүн: **{amount:,}** ₮\nТатвар ({rate}%): **{tax:,}** ₮\nХүлээн авах дүн: **{final_amount:,}** ₮",
                              color=GOLD_COLOR)
        view = ConfirmView()
        await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is not True:
            return await ctx.send("❌ Шилжүүлэг цуцлагдлаа.")
        # Баталгаажуулах хугацаанд үлдэгдэл өөрчлөгдсөн байж болзошгүй тул
        # шилжүүлэг хийхийн өмнө дахин шалгана (TOCTOU давхар шилжүүлэг үүсгэхээс сэргийлэх)
        sender_bal = await self.get_balance(ctx.author.id, ctx.guild.id)
        if sender_bal < amount:
            return await ctx.send(embed=discord.Embed(
                title="❌ Алдаа",
                description=f"Баталгаажуулах хугацаанд үлдэгдэл өөрчлөгдсөн тул шилжүүлэг цуцлагдлаа. Одоогийн үлдэгдэл: {sender_bal:,}₮",
                color=ERROR_COLOR,
            ))
        sender_before = await self.get_balance(ctx.author.id, ctx.guild.id)
        receiver_before = await self.get_balance(member.id, ctx.guild.id)
        # Хоёр хэрэглэгчийн lock-ыг бүх debit+credit үеэр тэгш өршөөд
        # барина: хоёр бичигдэл алдаагаар салдагдахгүй, нэг хосын хоёр
        # шилжүүлэг давхцахгүй. Дараалал тогтмол тул A->B ба B->A зэрэг
        # үед deadlock үүсэхгүй.
        parties = sorted(
            [(ctx.author.id, ctx.guild.id), (member.id, ctx.guild.id)],
            key=lambda p: f"{p[0]}:{p[1]}",
        )
        # Боломжит бол атомар RPC-ээр (migration 009) шилжилгээ хийнэ: хоёр
        # бичигдэл нэг transaction-д, давхар дуудахад reference-ээр хамгаалагдана.
        # RPC байхгүй бол lock-тэй хоёр бичигдлийн зам руу буцана.
        reference = f"transfer:{ctx.guild.id}:{ctx.author.id}:{getattr(ctx.message, 'id', 'nomsg')}"
        moved = await self._transfer_principal(
            ctx.author.id, ctx.guild.id, member.id, amount, tax, reference,
        )
        if moved is not None:
            sender_after, receiver_after = moved
            tax_shipped_by_rpc = True
        else:
            tax_shipped_by_rpc = False
            async with self._balance_guard(*parties[0]), self._balance_guard(*parties[1]):
                sender_after = await self.update_balance(ctx.author.id, ctx.guild.id, -amount, apply_tax=False)
                receiver_after = await self.update_balance(member.id, ctx.guild.id, final_amount, apply_tax=False)
        # Шилжүүлгийн татвар Ерөнхийлөгч/Захирал rolт хэрэглэгчид очно
        if tax > 0 and not tax_shipped_by_rpc:
            try:
                await self.distribute_tax(ctx.guild.id, tax)
            except Exception as exc:
                # Шилжүүлэг аль хэдийн хийгдсэн тул татварын алдаа нь
                # шилжүүлгийг амжилтанд хүргэхгүй.
                logger.warning("transfer tax distribution failed gid=%s: %s", ctx.guild.id, exc, exc_info=True)
        await self.record_money(ctx.guild.id, ctx.author.id, ctx.author.id, "transfer_out", -amount,
                                sender_before, sender_after, f"To {member.id}", f"tax={tax}")
        await self.record_money(ctx.guild.id, member.id, ctx.author.id, "transfer_in", final_amount,
                                receiver_before, receiver_after, f"From {ctx.author.id}", f"tax={tax}")
        success_embed = discord.Embed(title="✅ ГҮЙЛГЭЭ АМЖИЛТТАЙ!",
                                      description=f"{ctx.author.mention} → {member.mention} **{amount:,}** ₮ шилжүүллээ.",
                                      color=SUCCESS_COLOR)
        await ctx.send(embed=success_embed)
        try: await member.send(f"📨 {ctx.author.display_name} танд **{final_amount:,}** ₮ шилжүүллээ!")
        except discord.HTTPException:
            logger.debug("Transfer receipt could not be delivered", exc_info=True)

    @commands.hybrid_command(name='deposit', aliases=['dep'])
    async def deposit(self, ctx, amount_str: str):
        if not await self.check_registration(ctx): return
        cash = await self.get_balance(ctx.author.id, ctx.guild.id)
        if amount_str.lower() == 'all': amt = cash
        else:
            try: amt = int(amount_str)
            except ValueError:
                return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Дүн нь тоо эсвэл 'all' байх ёстой.", color=ERROR_COLOR))
        if amt <= 0 or cash < amt:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Дүн буруу эсвэл мөнгө хүрэлцэхгүй.", color=ERROR_COLOR))
        bank = await self.get_bank(ctx.author.id, ctx.guild.id)
        if bank + amt > self.max_balance:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Банкны хязгаарт хүрнэ.", color=ERROR_COLOR))
        try:
            old_cash = cash
            new_cash, new_bank = await self.move_cash_and_bank(ctx.author.id, ctx.guild.id, amt, to_bank=True)
        except ValueError:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Үлдэгдэл өөрчлөгдсөн тул дахин оролдоно уу.", color=ERROR_COLOR))
        await self.record_money(ctx.guild.id, ctx.author.id, ctx.author.id, "deposit", -amt,
                                old_cash, new_cash, "Cash to bank")
        embed = discord.Embed(title="🏦 БАНКАНД ХАДГАЛАВ",
                              description=f"{ctx.author.mention} **{amt:,}** ₮ хадгаллаа.",
                              color=SUCCESS_COLOR,
                              timestamp=datetime.now(UTC))
        embed.add_field(name="💰 Шинэ банкны үлдэгдэл", value=f"**{new_bank:,}** ₮")
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='withdraw', aliases=['with'])
    async def withdraw(self, ctx, amount_str: str):
        if not await self.check_registration(ctx): return
        bank = await self.get_bank(ctx.author.id, ctx.guild.id)
        if amount_str.lower() == 'all': amt = bank
        else:
            try: amt = int(amount_str)
            except ValueError:
                return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Дүн нь тоо эсвэл 'all' байх ёстой.", color=ERROR_COLOR))
        if amt <= 0 or bank < amt:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Дүн буруу эсвэл банканд мөнгө хүрэлцэхгүй.", color=ERROR_COLOR))
        cash = await self.get_balance(ctx.author.id, ctx.guild.id)
        if cash + amt > self.max_balance:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Гар дээрх хязгаарт хүрнэ.", color=ERROR_COLOR))
        try:
            old_cash = cash
            new_cash, _ = await self.move_cash_and_bank(ctx.author.id, ctx.guild.id, amt, to_bank=False)
        except ValueError:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Үлдэгдэл өөрчлөгдсөн тул дахин оролдоно уу.", color=ERROR_COLOR))
        await self.record_money(ctx.guild.id, ctx.author.id, ctx.author.id, "withdraw", amt,
                                old_cash, new_cash, "Bank to cash")
        embed = discord.Embed(title="🏦 БАНКНААС АВЛАА",
                              description=f"{ctx.author.mention} **{amt:,}** ₮ авлаа.",
                              color=SUCCESS_COLOR,
                              timestamp=datetime.now(UTC))
        embed.add_field(name="💰 Шинэ гар дээрх үлдэгдэл", value=f"**{new_cash:,}** ₮")
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='eat')
    async def eat(self, ctx):
        if not await self.check_registration(ctx): return
        bal = await self.get_balance(ctx.author.id, ctx.guild.id)
        cost = 1500
        if bal < cost: return await ctx.send(embed=discord.Embed(title="❌ Мөнгө хүрэлцэхгүй", description=f"Хоолны үнэ {cost:,} ₮.", color=ERROR_COLOR))
        hunger, _ = await self.get_hunger_mood(ctx.author.id, ctx.guild.id)
        if hunger == 0: return await ctx.send(embed=discord.Embed(title="🍔 Цадсан", description="Та аль хэдийн цадсан байна!", color=WARNING_COLOR))
        await self.update_balance(ctx.author.id, ctx.guild.id, -cost)
        new_hunger = max(0, hunger-50)
        await self.set_hunger_mood(ctx.author.id, ctx.guild.id, hunger=new_hunger)
        embed = discord.Embed(title="🍔 ХООЛ ИДЭВ",
                              description=f"Өлсгөлөн **{hunger}** → **{new_hunger}**",
                              color=SUCCESS_COLOR,
                              timestamp=datetime.now(UTC))
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='relax')
    async def relax(self, ctx):
        if not await self.check_registration(ctx): return
        _, mood = await self.get_hunger_mood(ctx.author.id, ctx.guild.id)
        if mood == 0: return await ctx.send(embed=discord.Embed(title="🧘 Тайван", description="Та аль хэдийн тайван байна!", color=WARNING_COLOR))
        new_mood = max(0, mood-40)
        await self.set_hunger_mood(ctx.author.id, ctx.guild.id, mood=new_mood)
        embed = discord.Embed(title="🧘 АМРАВ",
                              description=f"Уур бухимдал **{mood}** → **{new_mood}**",
                              color=SUCCESS_COLOR,
                              timestamp=datetime.now(UTC))
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='bankprotect', aliases=['bp', 'block'])
    async def bank_protect(self, ctx):
        if not await self.check_registration(ctx): return
        rem = await self.get_bank_protection_remaining(ctx.author.id, ctx.guild.id)
        if rem > 0:
            hours, minutes = rem//3600, (rem%3600)//60
            return await ctx.send(embed=discord.Embed(title="🛡️ БАНК ХАМГААЛАГДСАН", description=f"Үлдсэн: {hours}ц {minutes}м", color=WARNING_COLOR))
        await self.set_bank_protection(ctx.author.id, ctx.guild.id, hours=2)
        embed = discord.Embed(title="🛡️ БАНК АМЖИЛТТАЙ ХАМГААЛАГДЛАА",
                              description="2 цагийн турш хулгай, татвараас хамгаалагдлаа!",
                              color=SUCCESS_COLOR,
                              timestamp=datetime.now(UTC))
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='bail', aliases=['шоронгоосгарах', 'bailout'])
    async def bail(self, ctx):
        if not await self.check_registration(ctx): return
        if not await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send(embed=discord.Embed(title="❌ АЛДАА", description="Та шоронд байхгүй байна!", color=ERROR_COLOR))
        fine = 5000
        bal = await self.get_balance(ctx.author.id, ctx.guild.id)
        if bal < fine:
            return await ctx.send(embed=discord.Embed(
                title="❌ МӨНГӨ ХҮРЭЛЦЭХГҮЙ",
                description=f"Таны гар дээр {fine:,}₮ байхгүй байна. Одоогийн үлдэгдэл: {bal:,}₮",
                color=ERROR_COLOR
            ))
        await self.update_balance(ctx.author.id, ctx.guild.id, -fine)
        await self.bot.db_manager.update("economy", {"user_id": str(ctx.author.id), "guild_id": str(ctx.guild.id)}, {"prison_until": 0})
        embed = discord.Embed(title="🕊️ ШОРОНГООС ГАРЛАА",
                              description=f"{ctx.author.mention} та **{fine:,}₮** төлж шоронгоос гарлаа.",
                              color=SUCCESS_COLOR,
                              timestamp=datetime.now(UTC))
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='prison', aliases=['jail'])
    async def prison_status(self, ctx):
        if not await self.check_registration(ctx): return
        remaining = await self.get_prison_remaining(ctx.author.id, ctx.guild.id)
        if remaining <= 0:
            return await ctx.send(embed=discord.Embed(title="✅ ЧӨЛӨӨТЭЙ", description="Та одоогоор шоронд байхгүй байна.", color=SUCCESS_COLOR))
        minutes, seconds = divmod(remaining, 60)
        hours, minutes = divmod(minutes, 60)
        total = max(1, hours * 60 + minutes + 1)
        filled = min(10, max(0, int((total - (hours * 60 + minutes)) / total * 10)))
        embed = discord.Embed(title="🚔 ШОРООНЫ СТАТУС", color=ERROR_COLOR)
        embed.description = f"{ctx.author.mention}, та одоогоор ял эдэлж байна.\n\n⏱️ Үлдсэн хугацаа: **{hours}ц {minutes}м {seconds}с**\n🔒 Төлөв: **PRISONER**\n`{'█' * filled}{'░' * (10 - filled)}`"
        embed.add_field(name="Зөвшөөрөгдөх", value="`prison-work`, `bail`, `prison`", inline=False)
        embed.add_field(name="Хориглогдох", value="Casino, bet game, transfer, crime", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='prison-work', aliases=['jailwork'])
    async def prison_work(self, ctx):
        if not await self.check_registration(ctx): return
        key = f"{ctx.guild.id}:{ctx.author.id}"
        lock = self._prison_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._prison_locks[key] = lock
        async with lock:
            remaining = await self.get_prison_remaining(ctx.author.id, ctx.guild.id)
            if remaining <= 0:
                return await ctx.send("✅ Та шоронд байхгүй байна.")
            last = self._prison_work_last.get(key, 0)
            if int(time.time()) - last < 900:
                wait = 900 - (int(time.time()) - last)
                return await ctx.send(f"⏳ Дараагийн prison work хүртэл {wait // 60} минут үлдлээ.")
            reduction = min(15 * 60, remaining)
            reward = 250
            await self.bot.db_manager.update(
                "economy", {"user_id": str(ctx.author.id), "guild_id": str(ctx.guild.id)},
                {"prison_until": int(time.time()) + remaining - reduction},
            )
            self._prison_work_last[key] = int(time.time())
            await self.update_balance(ctx.author.id, ctx.guild.id, reward, apply_tax=False)
        await ctx.send(embed=discord.Embed(
            title="🧹 ШОРООНЫ АЖИЛ ДУУСЛАА",
            description=f"Ялын хугацаа **15 минут** багаслаа.\n💰 Reward: **+{reward:,}₮**",
            color=SUCCESS_COLOR,
        ))

    @commands.hybrid_command(name='prison-appeal', aliases=['appeal'])
    async def prison_appeal(self, ctx):
        if not await self.check_registration(ctx): return
        if not await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send("✅ Та шоронд байхгүй байна.")
        await ctx.send(embed=discord.Embed(
            title="📨 ӨРГӨДӨЛ БҮРТГЭГДЛЭЭ",
            description="Таны prison appeal хүсэлт админд мэдэгдлээ. Давхар хүсэлт илгээхгүй байна.",
            color=INFO_COLOR,
        ))

    @commands.hybrid_command(name='jobs', aliases=['ajil', 'ажил'])
    async def jobs_list(self, ctx):
        """Бүх ажлын түвшин ба цалинг харах."""
        lines = []
        for req in sorted(JOB_LEVELS.keys()):
            job = JOB_LEVELS[req]
            lines.append(f"`Lvl {req:>3}` {job['emoji']} {job['name']} — {job['min']:,}-{job['max']:,} ₮")
        embed = discord.Embed(
            title=f"💼 АЖЛЫН ЖАГСААЛТ ({len(lines)} ажил)",
            description="Discord түвшин өндөрлөх тусам илүү өндөр цалинтай ажилд орох боломжтой.",
            color=GOLD_COLOR,
        )
        chunk = []
        for i, line in enumerate(lines, 1):
            chunk.append(line)
            if len(chunk) == 12 or i == len(lines):
                embed.add_field(name="\u200b", value="\n".join(chunk), inline=False)
                chunk = []
        embed.set_footer(text=f"Таны одоогийн ажлыг харах: {ctx.prefix}balance")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='taxinfo', aliases=['татвар'])
    async def tax_info(self, ctx):
        """Татварын системийн мэдээлэл."""
        gid = ctx.guild.id
        collectors = await self.get_tax_collectors(gid)
        embed = discord.Embed(title="🏛️ ТАТВАРЫН СИСТЕМ", color=GOLD_COLOR)
        embed.add_field(name="📊 Татварын хувь", value=f"**{self.transfer_tax_percent}%** (нийт орлогод)", inline=True)
        embed.add_field(name="💰 Энэ сессийн цугларсан", value=f"**{self._tax_collected.get(gid, 0):,}** ₮", inline=True)
        embed.add_field(name="📤 Хуваарилсан", value=f"**{self._tax_distributed.get(gid, 0):,}** ₮", inline=True)
        if collectors:
            embed.add_field(
                name="👑 Татвар хүлээн авагч",
                value="\n".join(f"{m.mention} — {m.display_name}" for m in collectors[:10]),
                inline=False,
            )
        else:
            embed.add_field(
                name="👑 Татвар хүлээн авагч",
                value=f"Байхгүй! `{', '.join(self._collector_role_names)}` ролуудын аль нэгийг зүүсэн хэрэглэгч татварын орлогыг авна.",
                inline=False,
            )
        embed.set_footer(text="Татвар автоматаар цугларч, тухайн ролттой хэрэглэгчийн дансанд ордог.")
        await ctx.send(embed=embed)

    async def _wealth_role_loop(self):
        """Балансаас хамаарч Ядуу/Дундаж/Саятан/Тэрбумтан ролуудыг автоматаар олгох."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                for guild in self.bot.guilds:
                    try:
                        await self._update_wealth_roles(guild)
                    except Exception:
                        logger.exception("Operation failed in _wealth_role_loop")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Operation failed in _wealth_role_loop")
            await asyncio.sleep(300)

    async def _update_wealth_roles(self, guild: discord.Guild):
        if not guild.me.guild_permissions.manage_roles:
            return
        rows = await self.bot.db_manager.fetch_all(
            "economy", {"guild_id": str(guild.id)},
            selects="user_id, balance, bank_balance",
        )
        if not rows:
            return
        role_objs = {}
        for name, _threshold, color in WEALTH_ROLES:
            role = discord.utils.find(lambda r, n=name: r.name.lower() == n.lower(), guild.roles)
            if role is None:
                try:
                    role = await guild.create_role(name=name, color=discord.Color(color), reason="Санхүүгийн зэрэглэлийн роль")
                except discord.Forbidden:
                    return
                except discord.HTTPException:
                    continue
            role_objs[name] = role
        bot_top = guild.me.top_role.position
        for row in rows:
            try:
                member = guild.get_member(int(row["user_id"]))
            except (ValueError, TypeError):
                continue
            if not member or member.bot:
                continue
            total = (row.get("balance") or 0) + (row.get("bank_balance") or 0)
            target_name = None
            for name, threshold, _c in WEALTH_ROLES:
                if total >= threshold:
                    target_name = name
                    break
            target = role_objs.get(target_name) if target_name else None
            to_remove = [
                r for r in member.roles
                if r.name in role_objs and (target is None or r.id != target.id)
            ]
            if target and target not in member.roles and target.position < bot_top:
                try:
                    await member.add_roles(target, reason=f"Санхүүгийн зэрэглэл: {target_name}")
                except discord.HTTPException:
                    pass
            if to_remove:
                try:
                    await member.remove_roles(*to_remove, reason="Санхүүгийн зэрэглэл өөрчлөгдлөө")
                except discord.HTTPException:
                    pass

    async def _role_income_loop(self):
        await self.bot.wait_until_ready()
        self._role_income_last = {}
        while not self.bot.is_closed():
            try:
                rows = await self.bot.db_manager.fetch_safe("role_income")
                now = int(time.time())
                for r in rows:
                    guild_id, role_id, amount, interval = r["guild_id"], r["role_id"], r["amount"], r["interval_seconds"]
                    interval = int(interval or 0)
                    if interval > 0:
                        key = f"{guild_id}:{role_id}"
                        last = self._role_income_last.get(key, 0)
                        if now - last < interval:
                            continue
                    guild = self.bot.get_guild(int(guild_id))
                    if not guild: continue
                    role = guild.get_role(int(role_id))
                    if not role: continue
                    paid = False
                    for member in role.members:
                        if not member.bot:
                            await self.update_balance(member.id, guild.id, amount)
                            paid = True
                    if interval > 0 and paid:
                        self._role_income_last[f"{guild_id}:{role_id}"] = now
            except Exception:
                logger.exception("Role income loop error (table may be missing)")
            await asyncio.sleep(60)

# ---------- VIEWS & MODALS ----------
class ConfirmView(View):
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.value = None
    @discord.ui.button(label="Тийм ✅", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        self.value = True
        self.stop()
        await interaction.response.defer()
    @discord.ui.button(label="Үгүй ❌", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        self.value = False
        self.stop()
        await interaction.response.defer()

async def _admin_panel_allowed(interaction: discord.Interaction, author_id: int, guild_id: int) -> bool:
    """Gate for the publicly posted economy admin panel and its modals.

    The commands that open the panel are admin-gated, but the panel message
    is posted publicly, so the buttons and the modals they open have to
    re-check who is actually acting.
    """
    if interaction.guild is None or interaction.guild.id != guild_id:
        await interaction.response.send_message("❌ Энэ самбар өөр серверийнх байна.", ephemeral=True)
        return False
    if interaction.user.id != author_id:
        await interaction.response.send_message("❌ Энэ самбар таных биш.", ephemeral=True)
        return False
    # guild_permissions нь зөвхөн серверийн гишүүнд байдаг тул орхигдсон
    # эсвэл None бол "эрхгүй" гэж үзнэ (ганц хэрэглэгчийн эрх шалгах).
    permissions = getattr(interaction.user, "guild_permissions", None)
    if permissions is None or not permissions.administrator:
        await interaction.response.send_message("❌ Administrator эрх шаардлагатай.", ephemeral=True)
        return False
    return True


class AdminPanelView(View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await _admin_panel_allowed(interaction, self.ctx.author.id, self.ctx.guild.id)

    async def on_timeout(self):
        await disable_setup_panel(self, self.message)

    @discord.ui.button(label="⏱ Cooldown", style=discord.ButtonStyle.grey)
    async def cooldown_btn(self, interaction: discord.Interaction, button: Button):
        modal = CooldownModal(self.ctx.author.id, self.ctx.guild.id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="💸 Торгууль", style=discord.ButtonStyle.grey)
    async def fine_btn(self, interaction: discord.Interaction, button: Button):
        modal = FineModal(self.ctx.author.id, self.ctx.guild.id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="💰 Цалин (Payout)", style=discord.ButtonStyle.grey)
    async def payout_btn(self, interaction: discord.Interaction, button: Button):
        modal = PayoutModal(self.ctx.author.id, self.ctx.guild.id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🎲 Бүтэлгүйтэх %", style=discord.ButtonStyle.grey)
    async def failrate_btn(self, interaction: discord.Interaction, button: Button):
        modal = FailRateModal(self.ctx.author.id, self.ctx.guild.id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="💬 Custom Reply", style=discord.ButtonStyle.blurple)
    async def reply_btn(self, interaction: discord.Interaction, button: Button):
        modal = CustomReplyModal(self.ctx.author.id, self.ctx.guild.id)
        await interaction.response.send_modal(modal)

class _AdminConfigModal(Modal):
    """Base for the admin economy config modals.

    The panel that opens these modals is posted publicly, so the modal
    re-checks that the submitter is the administrator who opened the panel.
    """

    def __init__(self, author_id: int, guild_id: int):
        super().__init__()
        self.author_id = author_id
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await _admin_panel_allowed(interaction, self.author_id, self.guild_id)


class CooldownModal(_AdminConfigModal, title="Cooldown тохируулах"):
    command = TextInput(label="Командын нэр", placeholder="work", required=True)
    seconds = TextInput(label="Cooldown (секунд)", placeholder="3600", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        try:
            cog = interaction.client.get_cog("Economy")
            cmd = self.command.value.lower()
            sec = int(self.seconds.value)
            # Сөрөг cooldown нь "хэзээ ч болохгүй" гэсэн үг бөгөөд
            # rate limit-ийг бүрэн илгүй болгоно. 0 бол зөвшөөрөгдөнө.
            if sec < 0 or sec > 86400:
                raise ValueError("cooldown out of range")
            await interaction.response.defer(ephemeral=True)
            await cog.set_cooldown_cmd(interaction, cmd, sec)
            await interaction.followup.send(f"✅ `{cmd}` cooldown {sec}с боллоо.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Тоо оруулна уу (жишээ: 3600).", ephemeral=True)

class FineModal(_AdminConfigModal, title="Торгууль тохируулах"):
    command = TextInput(label="Командын нэр", placeholder="rob")
    fine_min = TextInput(label="Min торгууль", placeholder="100")
    fine_max = TextInput(label="Max торгууль", placeholder="500")
    async def on_submit(self, interaction: discord.Interaction):
        try:
            cog = interaction.client.get_cog("Economy")
            cmd = self.command.value.lower()
            mn = int(self.fine_min.value)
            mx = int(self.fine_max.value)
            if mn < 0 or mx < mn:
                raise ValueError("invalid fine range")
            await interaction.response.defer(ephemeral=True)
            await cog.set_fine_amount(interaction, cmd, mn, mx)
            await interaction.followup.send(f"✅ `{cmd}` торгууль {mn}-{mx} боллоо.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Тоо оруулна уу (жишээ: 100, 500).", ephemeral=True)

class PayoutModal(_AdminConfigModal, title="Цалин тохируулах"):
    command = TextInput(label="Командын нэр", placeholder="work")
    payout_min = TextInput(label="Min цалин")
    payout_max = TextInput(label="Max цалин")
    async def on_submit(self, interaction: discord.Interaction):
        try:
            cog = interaction.client.get_cog("Economy")
            cmd = self.command.value.lower()
            mn = int(self.payout_min.value)
            mx = int(self.payout_max.value)
            if mn < 0 or mx < mn:
                raise ValueError("invalid payout range")
            await interaction.response.defer(ephemeral=True)
            await cog.set_payout(interaction, cmd, mn, mx)
            await interaction.followup.send(f"✅ `{cmd}` цалин {mn}-{mx} боллоо.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Тоо оруулна уу (жишээ: 100, 500).", ephemeral=True)

class FailRateModal(_AdminConfigModal, title="Бүтэлгүйтэх магадлал"):
    command = TextInput(label="Командын нэр")
    rate = TextInput(label="Магадлал (0-1)", placeholder="0.5")
    async def on_submit(self, interaction: discord.Interaction):
        try:
            cog = interaction.client.get_cog("Economy")
            cmd = self.command.value.lower()
            r = float(self.rate.value)
            # Алдааны текст "0-1 хооронд байна" гэж хэлдэг боловч
            # шалгалт байгаагүй тул бүтээхэд шалгана.
            if not (0.0 <= r <= 1.0):
                raise ValueError("fail rate out of range")
            await interaction.response.defer(ephemeral=True)
            await cog.set_fail_rate(interaction, cmd, r)
            await interaction.followup.send(f"✅ `{cmd}` бүтэлгүйтэх {r*100}% боллоо.", ephemeral=True)
        except (ValueError, TypeError):
            await interaction.response.send_message("❌ Буруу тоо. 0-1 хооронд оруулна уу (жишээ: 0.5).", ephemeral=True)

class CustomReplyModal(_AdminConfigModal, title="Custom Reply нэмэх"):
    command = TextInput(label="Команд")
    reply_type = TextInput(label="Төрөл (success/fail)")
    text = TextInput(label="Текст", style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Economy")
        await interaction.response.defer(ephemeral=True)
        await cog.add_reply(interaction, self.command.value, self.text.value, self.reply_type.value)
        await interaction.followup.send("✅ Custom reply нэмэгдлээ.", ephemeral=True)

class WorkPhraseView(View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=300)
        self.cog = cog
        self.ctx = ctx
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await _admin_panel_allowed(interaction, self.ctx.author.id, self.ctx.guild.id)

    async def on_timeout(self):
        await disable_setup_panel(self, self.message)

    @discord.ui.button(label="➕ Нэмэх", style=discord.ButtonStyle.green)
    async def add_phrase(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AddPhraseModal(self.cog, interaction.guild_id, self.ctx.author.id))

    @discord.ui.button(label="➖ Хасах", style=discord.ButtonStyle.red)
    async def remove_phrase(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(RemovePhraseModal(self.cog, interaction.guild_id, self.ctx.author.id))

    @discord.ui.button(label="📋 Жагсаалт", style=discord.ButtonStyle.blurple)
    async def list_phrases(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        rows = await self.cog.bot.db_manager.fetch_all("work_phrases", {"guild_id": str(interaction.guild_id)}, selects="id,phrase")
        if not rows:
            embed = discord.Embed(title="📋 Ажлын өгүүлбэрүүд", description="Хоосон", color=WARNING_COLOR)
        else:
            embed = discord.Embed(title="📋 Ажлын өгүүлбэрүүд", color=INFO_COLOR)
            for r in rows[:20]:
                embed.add_field(name=f"ID {r['id']}", value=r['phrase'], inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Бүгдийг устгах", emoji="🧹", style=discord.ButtonStyle.danger)
    async def clear_phrases(self, interaction: discord.Interaction, button: Button):
        confirmation = ConfirmActionView(
            interaction.user.id, interaction.guild_id, timeout=30
        )
        await interaction.response.send_message(
            "⚠️ Бүх ажлын өгүүлбэрийг буцаах боломжгүйгээр устгах уу?",
            view=confirmation,
            ephemeral=True,
        )
        timed_out = await confirmation.wait()
        if timed_out or not confirmation.confirmed:
            return await interaction.followup.send("Цэвэрлэх үйлдлийг цуцаллаа.", ephemeral=True)
        await self.cog.bot.db_manager.delete("work_phrases", {"guild_id": str(interaction.guild_id)})
        await interaction.followup.send("✅ Бүх өгүүлбэр устгагдлаа.", ephemeral=True)

class AddPhraseModal(Modal, title="Ажлын өгүүлбэр нэмэх"):
    phrase = TextInput(label="Өгүүлбэр (хамгийн ихдээ 160 тэмдэгт)", placeholder="Жишээ: Кофе чанаж байна", max_length=160, required=True)
    def __init__(self, cog, guild_id, author_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await _admin_panel_allowed(interaction, self.author_id, self.guild_id)
    async def on_submit(self, interaction: discord.Interaction):
        if len(self.phrase.value) > 160:
            return await interaction.response.send_message("❌ 160 тэмдэгтээс хэтрэхгүй байх ёстой.", ephemeral=True)
        await self.cog.bot.db_manager.insert("work_phrases", {"guild_id": str(self.guild_id), "phrase": self.phrase.value})
        await interaction.response.send_message(f"✅ Өгүүлбэр нэмэгдлээ: {self.phrase.value}", ephemeral=True)

class RemovePhraseModal(Modal, title="Өгүүлбэр хасах"):
    phrase_id = TextInput(label="ID дугаар", placeholder="Устгах өгүүлбэрийн ID", required=True)
    def __init__(self, cog, guild_id, author_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await _admin_panel_allowed(interaction, self.author_id, self.guild_id)
    async def on_submit(self, interaction: discord.Interaction):
        try:
            pid = int(self.phrase_id.value)
        except ValueError:
            return await interaction.response.send_message("❌ ID нь тоо байх ёстой.", ephemeral=True)
        await self.cog.bot.db_manager.delete("work_phrases", {"guild_id": str(self.guild_id), "id": pid})
        await interaction.response.send_message(f"✅ {pid} ID-тай өгүүлбэр устгагдлаа.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Economy(bot))
