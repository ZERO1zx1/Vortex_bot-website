"""Auto-moderation — анти-спам, антиссылка, анти-райд.
Тохиргоо: /automod toggle <функц> /automod status
Хадгалалт: Supabase automod_config хүснэгт (guild_id, feature, enabled)
i18n: guild lang-аар хариу

v2.5 засварууд:
- get_guild_lang async дуудлага засагдсан (await)
- re import module level-д
- RaidTracker: cooldown дуусахад deque цэвэрлэгдэнэ (memory leak засагдсан)
- asyncio.get_running_loop() хэрэглэнэ (deprecated loop засагдсан)
- Severity нэмэлт мөрийн цэвэрлэгээ
"""
import re
import time
import asyncio
from collections import defaultdict, deque
from utils.constants import SUCCESS_COLOR, WARNING_COLOR, ERROR_COLOR, INFO_COLOR
from utils.supabase_cog import SupabaseCog
from utils.i18n import t_direct, get_guild_lang
import discord
from discord.ext import commands, tasks
from discord import app_commands

TABLE = "automod_config"
FEATURES = ("antispam", "antilink", "antiraid")
DEFAULT_ON = ("antispam", "antilink")

URL_RE = re.compile(r"https?://[^\s]+")
INVITE_RE = re.compile(r"discord(?:\.gg|app\.com/invite|com/invite)/[A-Za-z0-9]+")

# Зөвшөөрөгдсөн domain жагсаалт (antilink-д хасагдахгүй)
ALLOWED_DOMAINS = {"github.com", "zero1zx1.github.io", "discord.gg", "discord.com"}

# Link зөвшөөрсөн category-ийн нэрний хэсгүүд (жишээ нь "💬┊линк-зона", "link-zone")
ALLOWED_LINK_CATS = {"линк-зона", "линк", "link", "link-zone", "links"}

# Spam severity: хэд дараалан зөрчсөн → timeout хугацаа (сек). 3+ → kick.
SPAM_SEVERITY = [60, 600, None]  # 1-р зөрчил 60с, 2-р 10мин, 3-р kick

NEW_ACCOUNT_HOURS = 7 * 24  # 7 хоногоос бага насантай аккаунт raid шинж гэж үзнэ


class AntiSpamTracker:
    """Мессежийн давтамж хянах + зөрчлийн тоо (severity)."""
    def __init__(self, limit=5, window=3.0):
        self.limit = limit
        self.window = window
        self.messages: dict[int, list[float]] = defaultdict(list)
        self.violations: dict[int, int] = defaultdict(int)

    def check(self, user_id: int) -> bool:
        now = time.time()
        lst = self.messages[user_id]
        lst = [t for t in lst if now - t < self.window]
        lst.append(now)
        self.messages[user_id] = lst
        return len(lst) > self.limit

    def violation(self, user_id: int) -> int:
        self.violations[user_id] += 1
        return self.violations[user_id]

    def cleanup(self):
        now = time.time()
        self.messages = {u: lst for u, lst in self.messages.items()
                         if any(now - t < self.window for t in lst)}
        # Window дотор мессеж илгээгээгүй хүний violation-г 0 болго
        self.violations = {u: v for u, v in self.violations.items()
                           if u in self.messages}


class RaidTracker:
    """Join давтамж хянах — deque ашиглаж O(N) болгоно."""
    def __init__(self, window=5.0, threshold=10):
        self.window = window
        self.threshold = threshold
        self.joins: dict[int, deque] = defaultdict(deque)
        self.acted: set[int] = set()  # guild_id — нэг raid-д олон удаа арга хэмжээ авахгүй

    def add(self, guild_id: int, user_id: int) -> list[int]:
        now = time.time()
        dq = self.joins[guild_id]
        dq.append((now, user_id))
        # Хуучин timestamp-уудыг хасна
        while dq and now - dq[0][0] > self.window:
            dq.popleft()
        if len(dq) < self.threshold:
            return []
        if guild_id in self.acted:
            return []  # энэ guild-д ойрын хугацаанд арга хэмжээ авсан
        self.acted.add(guild_id)
        # Сүүлийн 5 сек-д нэгдсэн бүх хүний ID буцаана
        return [uid for _, uid in dq]

    def cooldown_done(self, guild_id: int, delay=120.0):
        """Cooldown дууссаны дараа acted-ээс хасаж, deque-г цэвэрлэнэ (leak-ээс хамгаална)."""
        def _clear():
            self.acted.discard(guild_id)
            self.joins.pop(guild_id, None)
        # Python 3.13 стандартын дагуу зөвхөн get_running_loop() — deprecated
        # get_event_loop() fallback-гүй (running loop байхгүй үед call_later утгагүй)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Синхрон контекстоос дуудагдсан бол loop-г олох боломжгүй —
            # таймерийг алдахын оронд шууд цэвэрлэнэ (хадгалахын баталгаагүй)
            _clear()
            return
        loop.call_later(delay, _clear)


class AutoModeration(SupabaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.spam = AntiSpamTracker()
        self.enabled: dict[int, set[str]] = {}
        self.raid = RaidTracker()

    async def cog_load(self):
        await super().cog_load()
        try:
            # NOTE: PostgREST has no raw-SQL endpoint; table creation is done
            # via migrations (database/migrations/20260813_runtime_missing_tables.sql).
            # Ensure the table exists at least once by checking read access.
            await self.get_all_data(TABLE, {"guild_id": "__probe__"})
        except Exception as exc:
            logger.warning("automod_config хүснэгт олдсонгүй: %s — migration ажиллуул: 20260813_runtime_missing_tables.sql", exc)
        await self._load_all()
        self._periodic_cleanup.start()

    @tasks.loop(minutes=5)
    async def _periodic_cleanup(self):
        self.spam.cleanup()

    async def cog_unload(self):
        self._periodic_cleanup.cancel()
        await super().cog_unload()

    async def _load_all(self):
        for guild in self.bot.guilds:
            data = await self.get_all_data(TABLE, {"guild_id": str(guild.id)})
            enabled = {row["feature"] for row in data if row["enabled"]}
            if not enabled:
                enabled = set(DEFAULT_ON)
            self.enabled[guild.id] = enabled

    def is_on(self, guild_id: int, feature: str) -> bool:
        return feature in self.enabled.get(guild_id, set())

    # ══════════════ COMMANDS ══════════════
    @app_commands.command(name="automod", description="Auto-moderation тохиргоо")
    @app_commands.describe(action="Үйлдэл", feature="Функц")
    @app_commands.choices(action=[
        app_commands.Choice(name="Энэ функц тохируулах", value="toggle"),
        app_commands.Choice(name="Статус харуулах", value="status"),
    ])
    @app_commands.choices(feature=[
        app_commands.Choice(name="Анти-спам (5 мессеж/3 сек)", value="antispam"),
        app_commands.Choice(name="Антиссылка (зөвшөөрөгдөөгүй линк)", value="antilink"),
        app_commands.Choice(name="Анти-райд (5 сек-д 10+ гишүүн)", value="antiraid"),
    ])
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def automod(self, interaction: discord.Interaction, action: app_commands.Choice[str],
                      feature: app_commands.Choice[str]):
        guild_id = interaction.guild.id
        lang = await get_guild_lang(guild_id)
        feats = self.enabled.setdefault(guild_id, set(DEFAULT_ON))
        if action.value == "toggle":
            if feature.value in feats:
                feats.discard(feature.value)
                await self.db.execute(TABLE, {
                    "guild_id": str(guild_id), "feature": feature.value, "enabled": False,
                    "created_at": discord.utils.utcnow().isoformat()})
                desc = t_direct(lang, "am.off", feature_mn=feature.name)
            else:
                feats.add(feature.value)
                await self.db.execute(TABLE, {
                    "guild_id": str(guild_id), "feature": feature.value, "enabled": True,
                    "created_at": discord.utils.utcnow().isoformat()})
                desc = t_direct(lang, "am.on", feature_mn=feature.name)
            return await interaction.response.send_message(embed=discord.Embed(
                title="🛡️ Auto-moderation", description=desc, color=SUCCESS_COLOR))
        # status
        lines = [
            f"🛡️ **Анти-спам** — {'✅' if self.is_on(guild_id, 'antispam') else '❌'}",
            f"🔗 **Антиссылка** — {'✅' if self.is_on(guild_id, 'antilink') else '❌'}",
            f"🚨 **Анти-райд** — {'✅' if self.is_on(guild_id, 'antiraid') else '❌'}",
        ]
        await interaction.response.send_message(embed=discord.Embed(
            title="🛡️ Auto-moderation статус", description="\n".join(lines), color=INFO_COLOR))

    # ══════════════ LISTENERS ══════════════
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if message.author.guild_permissions.manage_messages:
            return  # staff-д exemption
        guild_id = message.guild.id
        if self.is_on(guild_id, "antispam") and self.spam.check(message.author.id):
            await self._handle_spam(message)
            return
        if self.is_on(guild_id, "antilink"):
            if URL_RE.search(message.content) or INVITE_RE.search(message.content):
                if not self._is_link_allowed(message):
                    await self._handle_link(message)

    def _is_link_allowed(self, message: discord.Message) -> bool:
        """Category нэр эсвэл URL domain allowlist-ээр зөвшөөрөх."""
        cat = message.channel.category
        if cat and any(k in cat.name.lower() for k in ALLOWED_LINK_CATS):
            return True
        for url in URL_RE.finditer(message.content):
            domain = url.group(0)[8:].lower()  # http(s):// хасах
            # query string-ийг хасах
            domain = domain.split("/", 1)[0].split("?", 1)[0]
            # subdomain-ийг шалгах: x.github.com → github.com
            parts = domain.split(".")
            if len(parts) >= 3:
                domain = ".".join(parts[-2:])
            if domain in ALLOWED_DOMAINS:
                return True
        return False

    async def _handle_spam(self, message: discord.Message):
        """Severity levels: warn → 60с → 10мин → kick."""
        level = self.spam.violation(message.author.id)
        reason = "Anti-spam (давтамж зөрчил)"
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        if level <= len(SPAM_SEVERITY) and SPAM_SEVERITY[level - 1] is not None:
            try:
                await message.author.timeout(discord.utils.utcnow(), SPAM_SEVERITY[level - 1], reason=reason)
            except discord.HTTPException:
                pass
        elif level > len(SPAM_SEVERITY):
            try:
                await message.author.kick(reason=reason + " (3+ зөрчил)")
            except discord.HTTPException:
                pass
        try:
            warn = await message.channel.send(
                embed=discord.Embed(title="🛡️ Анти-спам",
                                    description=f"{message.author.mention} хэт олон мессеж илгээлээ. "
                                                f"({level}-р зөрчил)",
                                    color=WARNING_COLOR))
            await asyncio.sleep(10)
            await warn.delete()
        except discord.HTTPException:
            pass

    async def _handle_link(self, message: discord.Message):
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        try:
            warn = await message.channel.send(
                embed=discord.Embed(title="🔗 Антиссылка",
                                    description=f"{message.author.mention} зөвшөөрөгдөөгүй линк илгээлээ.",
                                    color=WARNING_COLOR))
            await asyncio.sleep(10)
            await warn.delete()
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not self.is_on(member.guild.id, "antiraid"):
            return
        now = time.time()
        # Хуучин аккаунт (7 хоногоос бага насантай) бол raid шинж гэж үзнэ
        if member.created_at and (now - member.created_at.timestamp()) > NEW_ACCOUNT_HOURS * 3600:
            return
        joined_ids = self.raid.add(member.guild.id, member.id)
        if not joined_ids:
            return
        # Raid илэрсэн: бүгдийг 10 минутын timeout-д оруулна
        try:
            for uid in joined_ids:
                m = member.guild.get_member(uid)
                if m and not m.is_timed_out():
                    await m.timeout(discord.utils.utcnow(), 600, reason="Anti-raid: масс нэгдэлт")
        except discord.HTTPException:
            pass
        # Staff-д мэдэгдэх (system_channel байхгүй үед crash-ээс хамгаална)
        target = member.guild.system_channel
        if target is not None:
            try:
                await target.send(embed=discord.Embed(
                    title="🚨 Анти-райд хамгаалалт идэвхжлээ",
                    description=f"Сүүлийн 5 секундэд 10+ гишүүн нэгдлээ. "
                                f"Бүгдийг 10 минутын timeout-д орууллаа. "
                                f"Шалгаж баталгаажуулаарай.",
                    color=ERROR_COLOR))
            except discord.HTTPException:
                pass
        # 2 минутын дараа дахин арга хэмжээ авах боломж олгоно
        self.raid.cooldown_done(member.guild.id)


async def setup(bot):
    await bot.add_cog(AutoModeration(bot))
