"""Auto-moderation — анти-спам, антиссылка, анти-райд.
Тохиргоо: /automod toggle <функц> /automod config <түвшин>
Хадгалалт: Supabase automod_config хүснэгт (guild_id, feature, enabled, created_at)
i18n: guild lang-аар хариу
"""
import time
import re
from collections import defaultdict
from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
from utils.supabase_cog import SupabaseCog
from utils.i18n import t_direct, get_guild_lang
import discord
from discord.ext import commands
from discord import app_commands

TABLE = "automod_config"
FEATURES = ("antispam", "antilink", "antiraid")
DEFAULT_ON = ("antispam", "antilink")

URL_RE = re.compile(r"https?://[^\s]+")
INVITE_RE = re.compile(r"discord(?:\.gg|app\.com/invite)/[A-Za-z0-9]+")


class AntiSpamTracker:
    """Мессежийн давтамж хянах."""
    def __init__(self, limit=5, window=3.0):
        self.limit = limit
        self.window = window
        self.messages: dict[int, list[float]] = defaultdict(list)

    def check(self, user_id: int) -> bool:
        now = time.time()
        lst = self.messages[user_id]
        lst = [t for t in lst if now - t < self.window]
        lst.append(now)
        self.messages[user_id] = lst
        return len(lst) > self.limit


class AutoModeration(SupabaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.spam = AntiSpamTracker()
        self.enabled: dict[int, set[str]] = {}  # guild_id -> enabled features
        self.raid_window = 5.0

    async def cog_load(self):
        await super().cog_load()
        await self.db.execute("sql", {"query": f"""
            CREATE TABLE IF NOT EXISTS {TABLE} (
                guild_id TEXT, feature TEXT, enabled BOOLEAN DEFAULT true,
                created_at TEXT, PRIMARY KEY (guild_id, feature))"""})
        await self._load_all()

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
        app_commands.Choice(name="Анти-райд (хэт олон нэг дор)", value="antiraid"),
    ])
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def automod(self, interaction: discord.Interaction, action: app_commands.Choice[str],
                      feature: app_commands.Choice[str]):
        guild_id = interaction.guild.id
        lang = get_guild_lang(guild_id)
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
        if not message.author.guild_permissions.manage_messages:
            guild_id = message.guild.id
            if self.is_on(guild_id, "antispam") and self.spam.check(message.author.id):
                try:
                    await message.delete()
                    warn = await message.channel.send(
                        embed=discord.Embed(title="🛡️ Анти-спам",
                                            description=f"{message.author.mention} хэт олон мессеж илгээлээ.",
                                            color=WARNING_COLOR))
                    await message.author.timeout(discord.utils.utcnow(), 60, reason="Anti-spam")
                except discord.HTTPException:
                    pass
                return
            if self.is_on(guild_id, "antilink") and (URL_RE.search(message.content) or INVITE_RE.search(message.content)):
                allowed = message.channel.category and "allowed" in (message.channel.category.name or "").lower()
                if not allowed:
                    try:
                        await message.delete()
                        warn = await message.channel.send(
                            embed=discord.Embed(title="🔗 Антиссылка",
                                                description=f"{message.author.mention} линк илгээх эрхгүй.",
                                                color=WARNING_COLOR))
                    except discord.HTTPException:
                        pass
                    return

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not self.is_on(member.guild.id, "antiraid"):
            return
        now = time.time()
        joined = [m for m in member.guild.members if m.joined_at is not None
                  and now - m.joined_at.timestamp() < self.raid_window]
        if len(joined) >= 10:
            try:
                await member.guild.system_channel.send(embed=discord.Embed(
                    title="🚨 Анти-райд",
                    description=f"{member.mention} нэгдлээ — сүүлийн 5 секундэд 10+ гишүүн нэгдсэн. Хянаарай.",
                    color=ERROR_COLOR))
            except discord.HTTPException:
                pass


async def setup(bot):
    await bot.add_cog(AutoModeration(bot))
