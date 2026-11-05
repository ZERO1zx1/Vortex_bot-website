import logging
import math
import platform
import time
from datetime import UTC, datetime

import discord
from discord import app_commands, ui
from discord.ext import commands

try:
    import psutil
except ImportError:
    psutil = None

from src.utils.constants import (
    EMBED_COLOR,
    ERROR_COLOR,
    GOLD_COLOR,
    INFO_COLOR,
    SUCCESS_COLOR,
    WARNING_COLOR,
)
from src.utils.embed_style import add_box_field, error_embed, style_embed
from src.utils.slash_context import SlashContext

logger = logging.getLogger(__name__)

ADMIN_PANEL_TIMEOUT = 600
CLEAR_MESSAGE_COUNT = 10


def _bot_latency_ms(bot) -> int:
    latency_ms = bot.latency * 1000
    return round(latency_ms) if math.isfinite(latency_ms) else 0


def channel_is_locked(guild: discord.Guild, channel) -> bool:
    """Return the effective @everyone send state for a panel channel."""
    overwrite = channel.overwrites_for(guild.default_role)
    if overwrite.send_messages is not None:
        return overwrite.send_messages is False
    return not channel.permissions_for(guild.default_role).send_messages


def channel_bot_permissions(guild: discord.Guild, channel):
    """Resolve bot permissions after channel overrides, as Discord applies them."""
    return channel.permissions_for(guild.me)


def build_admin_panel_embed(
    guild: discord.Guild,
    channel,
    user,
    bot_latency: int,
) -> discord.Embed:
    members = getattr(guild, "members", ())
    online_members = sum(
        1
        for member in members
        if getattr(member, "status", discord.Status.offline) not in (discord.Status.offline, "offline")
    )
    bot_permissions = channel_bot_permissions(guild, channel)
    permission_items = (
        ("Суваг удирдах", bot_permissions.manage_channels),
        ("Мессеж цэвэрлэх", bot_permissions.manage_messages),
        ("Зарлал илгээх", bot_permissions.send_messages),
        ("Түүх унших", bot_permissions.read_message_history),
        ("Embed харуулах", bot_permissions.embed_links),
    )
    permission_text = "  ".join(
        f"{'✅' if allowed else '❌'} {label}" for label, allowed in permission_items
    )
    healthy = all(allowed for _, allowed in permission_items)
    locked = channel_is_locked(guild, channel)

    embed = discord.Embed(
        title="🛡️ Админ удирдлагын самбар",
        description=(
            "> ✅ **Систем хэвийн**\n"
            "> 🔐 Administrator эрх шаардлагатай\n\n"
            "Серверийн шуурхай удирдлага. Улаан үйлдэл серверт шууд нөлөөлнө; "
            "мессеж цэвэрлэхийн өмнө баталгаажуулалт асууна."
        ),
        color=INFO_COLOR,
        timestamp=datetime.now(UTC),
    )
    embed.set_author(name="🛡️ Aether Admin Console")
    icon = getattr(guild, "icon", None)
    if icon:
        embed.set_thumbnail(url=icon.url)
    embed.add_field(
        name="📊 Сервер",
        value=(
            f"**Гишүүд**  `{guild.member_count or 0:,}`\n"
            f"**Онлайн**  `{online_members:,}`\n"
            f"**Сувгууд**  `{len(guild.channels):,}`"
        ),
        inline=True,
    )
    embed.add_field(
        name="⚙️ Ботын төлөв",
        value=(
            f"**Хоцролт**  `{bot_latency} ms`\n"
            f"**Төлөв**  `{'🟢 Хэвийн' if healthy else '🟡 Эрх дутуу'}`\n"
            f"**Самбар**  `10 минут идэвхтэй`"
        ),
        inline=True,
    )
    embed.add_field(
        name="📍 Одоогийн суваг",
        value=(
            f"{getattr(channel, 'mention', '#unknown')} — "
            f"**{'🔒 Түгжээтэй' if locked else '🔓 Нээлттэй'}**\n"
            "`Суваг түгжих` · `10 мессеж цэвэрлэх` · `Зарлал бичих`"
        ),
        inline=False,
    )
    embed.add_field(name="🔐 Ботын зөвшөөрөл", value=permission_text, inline=False)
    embed.set_footer(
        text=f"🔐 Нээсэн админ: {user.display_name} • Самбар 10 минут идэвхтэй",
        icon_url=user.display_avatar.url,
    )
    return embed


class AdminAnnounceModal(ui.Modal, title="Серверийн зарлал"):
    def __init__(self, guild_id: int | None = None):
        super().__init__()
        self.guild_id = guild_id
        self.announcement_title = ui.TextInput(
            placeholder="Жишээ: Серверийн шинэчлэл",
            max_length=100,
        )
        self.announcement_content = ui.TextInput(
            style=discord.TextStyle.paragraph,
            placeholder="Гишүүдэд хүргэх мэдээллээ тодорхой бичнэ үү…",
            max_length=2000,
        )
        self.add_item(
            ui.Label(
                text="Гарчиг",
                description="Зарлалын гол санааг товч бичнэ үү.",
                component=self.announcement_title,
            )
        )
        self.add_item(
            ui.Label(
                text="Агуулга",
                description="Гишүүдэд хүргэх бүрэн мэдээлэл.",
                component=self.announcement_content,
            )
        )

    async def on_submit(self, interaction: discord.Interaction):
        if (
            interaction.guild is None
            or (self.guild_id is not None and interaction.guild.id != self.guild_id)
            or not interaction.user.guild_permissions.administrator
        ):
            return await interaction.response.send_message(
                "❌ Энэ зарлалыг илгээх эрхгүй байна.", ephemeral=True
            )
        bot_permissions = channel_bot_permissions(interaction.guild, interaction.channel)
        if not bot_permissions.send_messages or not bot_permissions.embed_links:
            return await interaction.response.send_message(
                "❌ Ботод энэ сувагт `Send Messages` болон `Embed Links` эрх хэрэгтэй.",
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title=f"📢 {self.announcement_title.value}",
            description=self.announcement_content.value,
            color=GOLD_COLOR,
            timestamp=datetime.now(UTC),
        )
        embed.set_footer(
            text=f"Зарласан: {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        try:
            await interaction.channel.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, users=True, roles=True, replied_user=False
                ),
            )
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(
                "Admin panel announcement failed in guild %s",
                interaction.guild_id,
                exc_info=True,
            )
            return await interaction.followup.send(
                "❌ Зарлал илгээж чадсангүй. Ботын эрхийг шалгана уу.", ephemeral=True
            )
        await interaction.followup.send("✅ Зарлал энэ сувагт илгээгдлээ.", ephemeral=True)


class ClearMessagesConfirmView(ui.View):
    def __init__(self, panel, author_id: int):
        super().__init__(timeout=45)
        self.panel = panel
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Энэ баталгаажуулалт өөр админых байна.", ephemeral=True
            )
            return False
        return await self.panel.interaction_check(interaction)

    @ui.button(label="Тийм, цэвэрлэх", style=discord.ButtonStyle.danger, emoji="🧹")
    async def confirm(self, interaction: discord.Interaction, _button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        panel_message_id = getattr(self.panel.message, "id", None)
        message_ids = set()
        try:
            async for message in interaction.channel.history(limit=50):
                if message.id != panel_message_id:
                    message_ids.add(message.id)
                if len(message_ids) == CLEAR_MESSAGE_COUNT:
                    break
            if message_ids:
                deleted = await interaction.channel.purge(
                    limit=50,
                    check=lambda message: message.id in message_ids,
                    reason=f"Admin panel clear by {interaction.user} ({interaction.user.id})",
                )
            else:
                deleted = []
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(
                "Admin panel clear failed in guild %s",
                interaction.guild_id,
                exc_info=True,
            )
            return await interaction.followup.send(
                "❌ Мессеж цэвэрлэж чадсангүй. `Manage Messages` эрхийг шалгана уу.",
                ephemeral=True,
            )

        for child in self.children:
            child.disabled = True
        await interaction.edit_original_response(view=self)
        await interaction.followup.send(
            f"🧹 **{len(deleted)}** мессеж цэвэрлэлээ.", ephemeral=True
        )
        await self.panel.log_action(
            interaction, "Clear", f"{len(deleted)} мессеж цэвэрлэсэн"
        )
        self.stop()

    @ui.button(label="Болих", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _button: ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="Цэвэрлэх үйлдлийг цуцаллаа.", view=self)
        self.stop()


class AdminPanelView(ui.View):
    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__(timeout=ADMIN_PANEL_TIMEOUT)
        self.bot = bot
        self.guild_id = guild_id
        self.message = None

    def sync_channel_state(self, guild: discord.Guild, channel) -> None:
        locked = channel_is_locked(guild, channel)
        self.lockdown_button.label = "Суваг нээх" if locked else "Суваг түгжих"
        self.lockdown_button.emoji = "🔓" if locked else "🔒"
        self.lockdown_button.style = (
            discord.ButtonStyle.success if locked else discord.ButtonStyle.danger
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.guild.id != self.guild_id:
            await interaction.response.send_message(
                "❌ Энэ самбар өөр серверийнх байна.", ephemeral=True
            )
            return False
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ `Administrator` эрх шаардлагатай.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException):
                pass

    async def log_action(self, interaction: discord.Interaction, action: str, reason: str):
        moderation = self.bot.get_cog("Moderation")
        if moderation is None:
            return
        try:
            await moderation.log_to_mod_channel(
                interaction.guild, action, interaction.channel, interaction.user, reason
            )
        except (discord.Forbidden, discord.HTTPException):
            logger.warning("Could not write admin panel action to mod log", exc_info=True)

    @ui.button(label="Суваг түгжих", style=discord.ButtonStyle.danger, emoji="🔒", row=0)
    async def lockdown_button(self, interaction: discord.Interaction, _button: ui.Button):
        channel = interaction.channel
        if not hasattr(channel, "set_permissions"):
            return await interaction.response.send_message(
                "❌ Энэ төрлийн сувагт түгжээ солих боломжгүй.", ephemeral=True
            )
        bot_permissions = channel_bot_permissions(interaction.guild, channel)
        if not bot_permissions.manage_channels:
            return await interaction.response.send_message(
                "❌ Ботод `Manage Channels` эрх алга.", ephemeral=True
            )

        await interaction.response.defer()
        was_locked = channel_is_locked(interaction.guild, channel)
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = bool(was_locked)
        try:
            await channel.set_permissions(
                interaction.guild.default_role,
                overwrite=overwrite,
                reason=f"Admin panel toggle by {interaction.user} ({interaction.user.id})",
            )
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(
                "Admin panel lockdown failed in guild %s",
                interaction.guild_id,
                exc_info=True,
            )
            return await interaction.followup.send(
                "❌ Түгжээ сольж чадсангүй. Ботын роль болон эрхийг шалгана уу.",
                ephemeral=True,
            )

        self.sync_channel_state(interaction.guild, channel)
        embed = build_admin_panel_embed(
            interaction.guild,
            channel,
            interaction.user,
            _bot_latency_ms(self.bot),
        )
        await interaction.message.edit(embed=embed, view=self)
        result = "Сувгийг нээлээ." if was_locked else "Сувгийг түгжлээ."
        await interaction.followup.send(
            f"{'🔓' if was_locked else '🔒'} {result}", ephemeral=True
        )
        await self.log_action(interaction, "Unlock" if was_locked else "Lock", result)

    @ui.button(
        label="10 мессеж цэвэрлэх",
        style=discord.ButtonStyle.secondary,
        emoji="🧹",
        row=0,
    )
    async def clear_button(self, interaction: discord.Interaction, _button: ui.Button):
        bot_permissions = channel_bot_permissions(interaction.guild, interaction.channel)
        if not bot_permissions.manage_messages or not bot_permissions.read_message_history:
            return await interaction.response.send_message(
                "❌ Ботод `Manage Messages` болон `Read Message History` эрх хэрэгтэй.",
                ephemeral=True,
            )
        view = ClearMessagesConfirmView(self, interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Энэ сувгийн хамгийн сүүлийн **10 мессежийг** цэвэрлэх үү? "
            "Самбарын мессеж устахгүй.",
            view=view,
            ephemeral=True,
        )

    @ui.button(label="Зарлал бичих", style=discord.ButtonStyle.primary, emoji="📢", row=0)
    async def announce_button(self, interaction: discord.Interaction, _button: ui.Button):
        await interaction.response.send_modal(AdminAnnounceModal(self.guild_id))

    @ui.button(label="Шинэчлэх", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def refresh_button(self, interaction: discord.Interaction, _button: ui.Button):
        self.sync_channel_state(interaction.guild, interaction.channel)
        embed = build_admin_panel_embed(
            interaction.guild,
            interaction.channel,
            interaction.user,
            _bot_latency_ms(self.bot),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @ui.button(label="Хаах", style=discord.ButtonStyle.secondary, emoji="✖️", row=1)
    async def close_button(self, interaction: discord.Interaction, _button: ui.Button):
        await interaction.response.defer()
        await interaction.message.delete()
        self.stop()


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @commands.hybrid_command(
        name="adminpanel",
        aliases=["serverpanel"],
        description="Серверийн шуурхай админ самбарыг нээх",
    )
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def admin_panel(self, ctx: commands.Context):
        channel = ctx.channel
        if not hasattr(channel, "overwrites_for") or not hasattr(channel, "permissions_for"):
            return await ctx.send(
                "❌ Самбарыг text суваг дотор нээнэ үү.", ephemeral=True
            )

        view = AdminPanelView(self.bot, ctx.guild.id)
        view.sync_channel_state(ctx.guild, channel)
        embed = build_admin_panel_embed(
            ctx.guild,
            channel,
            ctx.author,
            _bot_latency_ms(self.bot),
        )
        view.message = await ctx.send(embed=embed, view=view)

    async def is_owner_or_co_owner(self, ctx):
        """Resolve global and per-guild ownership consistently.

        ``OWNER_ID``/``CO_OWNERS`` grant bot-wide access.  The live Discord
        guild owner and co-owners appointed through ``/government`` receive
        access only inside their own guild.
        """
        user_id = ctx.author.id
        if user_id in self.bot.owner_ids:
            return True

        guild = ctx.guild
        if guild is None:
            return False
        if user_id == guild.owner_id:
            return True

        government = self.bot.get_cog("Government")
        if government is not None:
            return await government.is_co_owner_id(guild.id, user_id)
        return False

    @commands.command(name='status')
    async def status(self, ctx: commands.Context):
        await ctx.defer()
        delta = datetime.now(UTC) - datetime.fromtimestamp(self.start_time, UTC)
        total = int(delta.total_seconds())
        days, rem = divmod(total, 86400)
        h, rem = divmod(rem, 3600)
        m, s = divmod(rem, 60)
        uptime = f"{days} хоног {h:02d}:{m:02d}:{s:02d}" if days else f"{h:02d}:{m:02d}:{s:02d}"
        latency_ms = self.bot.latency * 1000
        latency = round(latency_ms) if math.isfinite(latency_ms) else 0
        if psutil:
            cpu_usage = psutil.cpu_percent()
            ram_usage = psutil.virtual_memory().percent
        else:
            cpu_usage = "N/A"
            ram_usage = "N/A"

        embed = style_embed("Бот-ын төлөв", "Системын мэдээлэл", INFO_COLOR, "info")
        add_box_field(embed, "СЭЙТЭРХҮҮ", [
            f"╭ Ажилласан хугацаа\n╰→ {uptime}",
            f"╭ Хоцролт\n╰→ {latency}ms",
            f"╭ CPU ашиглалт\n╰→ {cpu_usage}%",
            f"╭ RAM ашиглалт\n╰→ {ram_usage}%",
            f"╭ Операцион систем\n╰→ {platform.system()}",
            f"╭ Python хувилбар\n╰→ {platform.python_version()}",
        ])
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='info')
    @commands.guild_only()
    async def info(self, ctx: commands.Context):
        await ctx.defer(ephemeral=False)
        if ctx.guild is None:
            return await ctx.send(embed=error_embed("АЛДАА", "Зөвхөн сервер дотор ашиглах боломжтой."))

        guild = ctx.guild
        total_members = guild.member_count
        humans = len([m for m in guild.members if not m.bot])
        bots = total_members - humans
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        roles = len(guild.roles) - 1
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count or 0
        verif_levels = {
            discord.VerificationLevel.none: "❌ Хязгаарлалтгүй",
            discord.VerificationLevel.low: "✅ Бага",
            discord.VerificationLevel.medium: "⚠️ Дунд",
            discord.VerificationLevel.high: "🔒 Өндөр",
            discord.VerificationLevel.highest: "🔒🔒 Хамгийн өндөр"
        }
        verif_level = verif_levels.get(guild.verification_level, "Тодорхойгүй")

        color = GOLD_COLOR if guild.premium_tier > 0 else EMBED_COLOR
        embed = style_embed(guild.name, "Серверийн дэлгэрэнгүй мэдээлэл", color, "info")

        if guild.banner:
            embed.set_image(url=guild.banner.url)
        elif guild.icon:
            embed.set_image(url=guild.icon.url)

        add_box_field(embed, "НЭГЖҮҮЛЭЛ", [
            f"╭ Эзэмшигч\n╰→ {guild.owner.mention} (`{guild.owner.name}`)",
            f"╭ Үүсгэсэн огноо\n╰→ {guild.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"╭ Серверийн ID\n╰→ {guild.id}",
        ])
        add_box_field(embed, "ГИШҮҮД", [
            f"╭ Жинхэнэ хүн\n╰→ {humans}",
            f"╭ Ботууд\n╰→ {bots}",
            f"╭ Нийт\n╰→ {total_members}",
        ])
        add_box_field(embed, "СУВГУУД", [
            f"╭ Текст сувгууд\n╰→ {text_channels}",
            f"╭ Дууны сувгууд\n╰→ {voice_channels}",
            f"╭ Категори\n╰→ {categories}",
        ])
        add_box_field(embed, "ҮҮРЭГ БА БУСТ", [
            f"╭ Роль\n╰→ {roles}",
            f"╭ Boost түвшин\n╰→ {boost_level} {'⭐' * boost_level if boost_level else '💨'}",
            f"╭ Boost тоо\n╰→ {boost_count}",
            f"╭ Баталгаажуулалт\n╰→ {verif_level}",
        ])
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @app_commands.command(name='rolelist', description='Role жагсаалт харах')
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def rolelist(self, interaction, member: discord.Member = None):
        ctx = SlashContext(interaction)
        await ctx.defer(ephemeral=False)
        if not ctx.guild:
            return
        roles = sorted([r for r in ctx.guild.roles if r.name != "@everyone"], key=lambda r: r.position, reverse=True)
        if not roles:
            embed = discord.Embed(title="🎭 **РОЛЬ БАЙХГҮЙ**", description="Энэ серверт @everyone-ээс өөр роль байхгүй.", color=WARNING_COLOR)
            return await ctx.send(embed=embed)
        embed = discord.Embed(title=f"🎭 **{ctx.guild.name} -ИЙН РОЛЬУУД**", description=f"Нийт **{len(roles)}** роль", color=EMBED_COLOR)
        chunks = [roles[i:i+10] for i in range(0, min(len(roles), 50), 10)]
        for idx, chunk in enumerate(chunks):
            value = ", ".join([r.mention for r in chunk])
            if len(value) > 1024:
                value = f"{len(chunk)} роль (жагсаалт хэт урт)"
            embed.add_field(name=f"📋 Роль бүлэг {idx+1}", value=value, inline=False)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @app_commands.command(name='addmoney', description='Мөнгө нэмэх')
    @app_commands.default_permissions(administrator=True)
    async def addmoney(self, interaction, member: discord.Member, amount: int):
        ctx = SlashContext(interaction)
        if not await self.is_owner_or_co_owner(ctx):
            embed = discord.Embed(title="⛔ ЭРХ ХҮРЭХГҮЙ", description="Зөвхөн бот эзэмшигч / хамт эзэмшигч", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        await ctx.defer(ephemeral=False)
        economy = self.bot.get_cog("Economy")
        if not economy:
            embed = discord.Embed(title="❌ АЛДАА", description="Эдийн засгийн систем ажиллахгүй байна.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        if amount <= 0:
            embed = discord.Embed(title="❌ АЛДАА", description="Дүн эерэг байх ёстой.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        await economy.ensure_user(member.id, ctx.guild.id)
        # Админы өгсөн дүнгээр шууд очих ёстой: apply_tax үндсэнээр
        # татвартай байсан тул хэрэглэгчид үзүүлсэн нийт дүнээс
        # 10% дутуу орж ирдэг байсан.
        await economy.update_balance(member.id, ctx.guild.id, amount, apply_tax=False)
        new_bal = await economy.get_balance(member.id, ctx.guild.id)
        embed = discord.Embed(title="✅ МӨНГӨ НЭМЭГДЛЭЭ", description=f"{ctx.author.mention} → {member.mention} **{amount:,}** мөнгө нэмлээ.", color=SUCCESS_COLOR)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2331/2331966.png")
        embed.add_field(name="💰 ШИНЭ ҮЛДЭГДЭЛ", value=f"```yaml\n{new_bal:,} мөнгө```", inline=False)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @app_commands.command(name='removemoney', description='Мөнгө хасах')
    @app_commands.default_permissions(administrator=True)
    async def removemoney(self, interaction, member: discord.Member, amount: int):
        ctx = SlashContext(interaction)
        if not await self.is_owner_or_co_owner(ctx):
            embed = discord.Embed(title="⛔ ЭРХ ХҮРЭХГҮЙ", description="Зөвхөн бот эзэмшигч / хамт эзэмшигч", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        await ctx.defer(ephemeral=False)
        economy = self.bot.get_cog("Economy")
        if not economy:
            embed = discord.Embed(title="❌ АЛДАА", description="Эдийн засгийн систем ажиллахгүй байна.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        if amount <= 0:
            embed = discord.Embed(title="❌ АЛДАА", description="Дүн эерэг байх ёстой.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        bal = await economy.get_balance(member.id, ctx.guild.id)
        if bal < amount:
            embed = discord.Embed(title="❌ ХАНГАЛТГҮЙ", description=f"{member.mention} -д **{amount:,}** мөнгө хасахад хангалтгүй.\n💰 Одоогийн үлдэгдэл: **{bal:,}** мөнгө", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        await economy.update_balance(member.id, ctx.guild.id, -amount)
        new_bal = await economy.get_balance(member.id, ctx.guild.id)
        embed = discord.Embed(title="⚠️ МӨНГӨ ХАСАГДЛАА", description=f"{ctx.author.mention} → {member.mention} **{amount:,}** мөнгө хаслаа.", color=WARNING_COLOR)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/190/190411.png")
        embed.add_field(name="💰 ШИНЭ ҮЛДЭГДЭЛ", value=f"```yaml\n{new_bal:,} мөнгө```", inline=False)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Admin(bot))
