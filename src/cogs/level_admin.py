"""Administrative controls backed by the active Leveling engine."""

import asyncio
import logging
import weakref

import discord
from discord import app_commands, ui
from discord.ext import commands

from src.cogs.leveling import Leveling, get_config, set_config
from src.utils.constants import GOLD_COLOR, INFO_COLOR
from src.utils.http_images import validate_image_url

log = logging.getLogger(__name__)
MAX_DB_INT = 2_147_483_647
_CONFIG_LOCKS: weakref.WeakValueDictionary[int, asyncio.Lock] = weakref.WeakValueDictionary()


def _is_bot_owner(bot, user_id: int) -> bool:
    return user_id in (getattr(bot, "owner_ids", None) or ()) or user_id == getattr(bot, "owner_id", None)


def _can_manage(bot, guild, user) -> bool:
    if guild is None:
        return False
    permissions = getattr(user, "guild_permissions", None)
    return (
        _is_bot_owner(bot, user.id)
        or user.id == guild.owner_id
        or bool(permissions and permissions.administrator)
    )


def _positive_int(value, maximum=MAX_DB_INT) -> int:
    number = int(value)
    if not 1 <= number <= maximum:
        raise ValueError("value is outside the supported positive integer range")
    return number


def _description(lines: list[str], empty: str) -> str:
    if not lines:
        return empty
    text = "\n".join(lines)
    return text if len(text) <= 3900 else text[:3850] + "\n… бусад түвшнийг дугаараар сонгоно уу."


async def _save_config(engine, guild_id: int, *, toggle=False, **updates):
    lock = _CONFIG_LOCKS.get(guild_id)
    if lock is None:
        lock = asyncio.Lock()
        _CONFIG_LOCKS[guild_id] = lock
    async with lock:
        # Cached dictionaries must not change before a successful database write.
        cfg = dict(await get_config(engine.bot.db_manager, guild_id))
        cfg.update(updates)
        if toggle:
            cfg["enabled"] = not cfg["enabled"]
        await set_config(engine.bot.db_manager, guild_id, cfg)
        return cfg


def _background_url(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    return validate_image_url(value)


async def _report_error(interaction: discord.Interaction, error: Exception):
    log.exception("Level admin interaction failed", exc_info=(type(error), error, error.__traceback__))
    try:
        if interaction.response.is_done():
            await interaction.followup.send("❌ Тохиргоог шинэчилж чадсангүй. Дахин оролдоно уу.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Тохиргоог шинэчилж чадсангүй. Дахин оролдоно уу.", ephemeral=True)
    except discord.HTTPException:
        log.debug("Level admin error response could not be delivered", exc_info=True)


class AdminView(ui.View):
    def __init__(self, engine: Leveling, ctx, *, timeout=600):
        super().__init__(timeout=timeout)
        self.cog = engine
        self.ctx = ctx
        self.guild_id = ctx.guild.id
        self.opener_id = ctx.author.id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (
            not self.is_finished()
            and interaction.guild_id == self.guild_id
            and interaction.user.id == self.opener_id
            and _can_manage(self.cog.bot, interaction.guild, interaction.user)
        ):
            return True
        await interaction.response.send_message(
            "⛔ Энэ самбарын эзэнд хүчинтэй админ эрх шаардлагатай.", ephemeral=True
        )
        return False

    async def build_embed(self):
        raise NotImplementedError

    async def refresh_message(self):
        if self.message is None:
            raise RuntimeError("the admin panel message has not been bound")
        embed = await self.build_embed()
        try:
            await self.message.edit(embed=embed, view=self)
        except discord.HTTPException:
            log.debug("Level admin panel could not be refreshed", exc_info=True)

    async def open_panel(self, interaction, panel):
        await interaction.response.defer(ephemeral=True, thinking=True)
        embed = await panel.build_embed()
        panel.message = await interaction.followup.send(embed=embed, view=panel, ephemeral=True, wait=True)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                log.debug("Level admin timeout update failed", exc_info=True)

    async def on_error(self, interaction, error, item):
        await _report_error(interaction, error)


class AdminModal(ui.Modal):
    def __init__(self, view: AdminView, *, title: str):
        super().__init__(title=title, timeout=300)
        self.panel = view

    async def interaction_check(self, interaction):
        return await self.panel.interaction_check(interaction)

    async def on_error(self, interaction, error):
        await _report_error(interaction, error)


class LevelNumberModal(AdminModal):
    level = ui.TextInput(label="Түвшин", placeholder="26", max_length=10)

    def __init__(self, view):
        super().__init__(view, title="Түвшин сонгох")

    async def on_submit(self, interaction):
        try:
            selected = _positive_int(self.level.value)
        except ValueError:
            return await interaction.response.send_message("❌ Эерэг бүхэл түвшин оруулна уу.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        self.panel.selected_level = selected
        await self.panel.refresh_message()
        await interaction.followup.send(f"✅ Түвшин {selected} сонгогдлоо.", ephemeral=True)


class LevelManagerView(AdminView):
    def __init__(self, engine, ctx):
        super().__init__(engine, ctx)
        self.selected_level = None
        # Populate level select options dynamically
        level_options = [discord.SelectOption(label=f"Level {level}", value=str(level)) for level in range(1, 26)]
        self.children[0].options = level_options  # type: ignore[index]

    @ui.select(
        placeholder="Түвшин сонгох (1–25, эсвэл 'Өөр түвшин')",
        options=[discord.SelectOption(label="…", value="1")],  # placeholder, replaced in __init__
        row=0,
    )
    async def level_select(self, interaction, select):
        self.selected_level = _positive_int(select.values[0])
        await interaction.response.send_message(f"✅ Түвшин {self.selected_level} сонгогдлоо.", ephemeral=True)

    @ui.button(label="🔢 Өөр түвшин", style=discord.ButtonStyle.secondary, row=4)
    async def custom_level(self, interaction, button):
        await interaction.response.send_modal(LevelNumberModal(self))


class RewardModal(AdminModal):
    money = ui.TextInput(label="Мөнгөн дүн (₮)", placeholder="5000", max_length=10)

    def __init__(self, view, level):
        super().__init__(view, title="Шагнал тохируулах")
        self.level = level

    async def on_submit(self, interaction):
        try:
            amount = _positive_int(self.money.value)
        except ValueError:
            return await interaction.response.send_message("❌ 1–2,147,483,647 хооронд бүхэл дүн оруулна уу.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.panel.cog.set_level_reward(self.panel.guild_id, self.level, amount)
        await self.panel.refresh_message()
        await interaction.followup.send(f"✅ Level {self.level} → {amount:,} ₮ тохируулагдлаа.", ephemeral=True)


class LevelRewardManagerView(LevelManagerView):
    async def build_embed(self):
        entries = await self.cog.get_level_rewards(self.guild_id)
        lines = [f"**Level {int(entry['level'])}** → {int(entry['money']):,} ₮" for entry in entries]
        embed = discord.Embed(
            title="🎁 Түвшний мөнгөн шагнал",
            description=_description(lines, "Одоогоор ямар ч шагнал тохируулаагүй байна."),
            color=GOLD_COLOR,
        )
        embed.set_footer(text="1–25 түвшнийг цэсээр, бусад түвшнийг 'Өөр түвшин' товчоор сонгоно уу.")
        return embed

    @ui.button(label="💰 Шагнал тохируулах", style=discord.ButtonStyle.green, row=1)
    async def set_reward_btn(self, interaction, button):
        if self.selected_level is None:
            return await interaction.response.send_message("❌ Эхлээд түвшин сонгоно уу.", ephemeral=True)
        await interaction.response.send_modal(RewardModal(self, self.selected_level))

    @ui.button(label="🗑️ Устгах", style=discord.ButtonStyle.red, row=1)
    async def remove_reward_btn(self, interaction, button):
        if self.selected_level is None:
            return await interaction.response.send_message("❌ Эхлээд түвшин сонгоно уу.", ephemeral=True)
        level = self.selected_level
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.cog.delete_level_reward(self.guild_id, level)
        await self.refresh_message()
        await interaction.followup.send(f"🗑️ Level {level} шагнал устгагдлаа.", ephemeral=True)


class LevelRoleManagerView(LevelManagerView):
    def __init__(self, engine, ctx):
        super().__init__(engine, ctx)
        self.selected_role = None

    async def build_embed(self):
        entries = await self.cog.get_level_roles(self.guild_id)
        lines = []
        for entry in entries:
            role_id = int(entry["role_id"])
            role = self.ctx.guild.get_role(role_id)
            role_text = role.mention if role else f"<@&{role_id}>"
            lines.append(f"**Level {int(entry['level'])}** → {role_text}")
        embed = discord.Embed(
            title="🛠️ Түвшний ролиудыг тохируулах",
            description=_description(lines, "Одоогоор ямар ч түвшний роль тохируулаагүй байна."),
            color=INFO_COLOR,
        )
        embed.set_footer(text="Түвшин/роль сонгоод 'Тохируулах' эсвэл 'Устгах' дарна уу.")
        return embed

    @ui.select(cls=ui.RoleSelect, placeholder="Роль сонгох", row=1)
    async def role_select(self, interaction, select):
        self.selected_role = select.values[0]
        await interaction.response.send_message(f"✅ Роль {self.selected_role.mention} сонгогдлоо.", ephemeral=True)

    @ui.button(label="✅ Тохируулах", style=discord.ButtonStyle.green, row=2)
    async def set_btn(self, interaction, button):
        if self.selected_level is None or self.selected_role is None:
            return await interaction.response.send_message("❌ Түвшин болон роль сонгоно уу.", ephemeral=True)
        role = interaction.guild.get_role(self.selected_role.id)
        bot_member = interaction.guild.me
        if (
            role is None or role.is_default() or role.managed or bot_member is None
            or not bot_member.guild_permissions.manage_roles or role >= bot_member.top_role
        ):
            return await interaction.response.send_message("❌ Бот олгох боломжтой роль сонгоно уу.", ephemeral=True)
        if (
            interaction.user.id != interaction.guild.owner_id
            and not _is_bot_owner(self.cog.bot, interaction.user.id)
            and role >= interaction.user.top_role
        ):
            return await interaction.response.send_message("❌ Өөрийн дээд ролиос доогуур роль сонгоно уу.", ephemeral=True)
        level = self.selected_level
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.cog.set_level_role(self.guild_id, level, role.id)
        await self.refresh_message()
        await interaction.followup.send(f"✅ Level {level} → {role.mention}", ephemeral=True)

    @ui.button(label="🗑️ Устгах", style=discord.ButtonStyle.red, row=2)
    async def remove_btn(self, interaction, button):
        if self.selected_level is None:
            return await interaction.response.send_message("❌ Түвшин сонгоно уу.", ephemeral=True)
        level = self.selected_level
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.cog.delete_level_role(self.guild_id, level)
        await self.refresh_message()
        await interaction.followup.send(f"🗑️ Level {level} роль тохиргоо устгагдлаа.", ephemeral=True)

    @ui.button(label="🎁 Шагнал", style=discord.ButtonStyle.blurple, row=3)
    async def reward_btn(self, interaction, button):
        await self.open_panel(interaction, LevelRewardManagerView(self.cog, self.ctx))


class ChannelPickerView(AdminView):
    def __init__(self, parent):
        super().__init__(parent.cog, parent.ctx, timeout=60)
        self.parent = parent

    @ui.select(
        cls=ui.ChannelSelect, placeholder="Мэдэгдэл сувгаа сонгоно уу",
        channel_types=[discord.ChannelType.text, discord.ChannelType.news],
    )
    async def channel_select(self, interaction, select):
        channel = interaction.guild.get_channel(select.values[0].id)
        bot_member = interaction.guild.me
        if channel is None or bot_member is None:
            return await interaction.response.send_message("❌ Суваг олдсонгүй.", ephemeral=True)
        permissions = channel.permissions_for(bot_member)
        if not (permissions.view_channel and permissions.send_messages and permissions.embed_links):
            return await interaction.response.send_message("❌ Бот энэ сувагт embed илгээх эрхгүй байна.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        await _save_config(self.cog, self.guild_id, announce_channel=channel.id)
        await self.parent.refresh_message()
        await interaction.followup.send("✅ Суваг тохируулагдлаа.", ephemeral=True)


class CooldownModal(AdminModal):
    message_seconds = ui.TextInput(label="Мессеж (секунд)", placeholder="60", max_length=10)
    reaction_seconds = ui.TextInput(label="Реакц (секунд)", placeholder="10", max_length=10)

    def __init__(self, view):
        super().__init__(view, title="Cooldown тохируулах")

    async def on_submit(self, interaction):
        try:
            message_seconds = _positive_int(self.message_seconds.value)
            reaction_seconds = _positive_int(self.reaction_seconds.value)
        except ValueError:
            return await interaction.response.send_message("❌ Эерэг бүхэл секунд оруулна уу.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        await _save_config(self.panel.cog, self.panel.guild_id, msg_cooldown=message_seconds, react_cooldown=reaction_seconds)
        await self.panel.refresh_message()
        await interaction.followup.send("✅ Cooldown шинэчлэгдлээ.", ephemeral=True)


class BackgroundModal(AdminModal):
    url = ui.TextInput(label="HTTP(S) зургийн URL (хоосон бол арилгана)", required=False, max_length=2000)

    def __init__(self, view):
        super().__init__(view, title="Арын зураг")

    async def on_submit(self, interaction):
        try:
            url = _background_url(self.url.value)
        except ValueError:
            return await interaction.response.send_message("❌ Нийтийн HTTP(S) зургийн URL оруулна уу.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        await _save_config(self.panel.cog, self.panel.guild_id, background_url=url)
        await self.panel.refresh_message()
        await interaction.followup.send("✅ Арын зураг шинэчлэгдлээ.", ephemeral=True)


class LevelingSetupView(AdminView):
    async def build_embed(self):
        cfg = await get_config(self.cog.bot.db_manager, self.guild_id)
        channel_id = cfg.get("announce_channel")
        channel = self.ctx.guild.get_channel(int(channel_id)) if channel_id else None
        embed = discord.Embed(title="🔧 Түвшний систем тохиргоо", color=INFO_COLOR)
        embed.add_field(name="📢 Мэдэгдэл суваг", value=channel.mention if channel else "Тохируулаагүй", inline=False)
        embed.add_field(name="Систем идэвхтэй", value="✅" if cfg["enabled"] else "❌")
        embed.add_field(name="Дуут XP", value="✅" if cfg["voice_xp_enabled"] else "❌")
        embed.add_field(name="Cooldown (msg/react)", value=f"{cfg['msg_cooldown']}с / {cfg['react_cooldown']}с")
        embed.add_field(name="Прогресс", value=f"{cfg['prog_type']} (base={cfg['prog_base']}, step={cfg['prog_step']})")
        embed.add_field(name="Урилгын XP", value=str(cfg.get("invite_xp", 0)))
        embed.add_field(name="Гэрлэлтийн урамшуулал", value=f"{cfg.get('marriage_bonus', 0.1) * 100}%")
        return embed

    @ui.button(label="📢 Суваг сонгох", style=discord.ButtonStyle.secondary, row=0)
    async def channel_btn(self, interaction, button):
        picker = ChannelPickerView(self)
        await interaction.response.send_message("Сувгаа сонгоно уу:", view=picker, ephemeral=True)
        picker.message = await interaction.original_response()

    @ui.button(label="🔄 Систем унтраах/асаах", style=discord.ButtonStyle.primary, row=0)
    async def toggle_btn(self, interaction, button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        cfg = await _save_config(self.cog, self.guild_id, toggle=True)
        await self.refresh_message()
        await interaction.followup.send(f"Систем {'ассан' if cfg['enabled'] else 'унтарсан'}.", ephemeral=True)

    @ui.button(label="⏱ Cooldown тохируулах", style=discord.ButtonStyle.secondary, row=1)
    async def cd_btn(self, interaction, button):
        await interaction.response.send_modal(CooldownModal(self))

    @ui.button(label="🎨 Арын зураг URL", style=discord.ButtonStyle.secondary, row=1)
    async def bg_btn(self, interaction, button):
        await interaction.response.send_modal(BackgroundModal(self))

    @ui.button(label="🎖️ Түвшний роль тохиргоо", style=discord.ButtonStyle.success, row=2)
    async def role_manager_btn(self, interaction, button):
        await self.open_panel(interaction, LevelRoleManagerView(self.cog, self.ctx))


class LevelAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _engine(self) -> Leveling | None:
        engine = self.bot.get_cog("Leveling")
        required = (
            "add_xp", "remove_xp", "get_level_roles", "set_level_role",
            "delete_level_role", "get_level_rewards", "set_level_reward", "delete_level_reward",
        )
        return engine if engine and all(callable(getattr(engine, method, None)) for method in required) else None

    async def _authorize(self, ctx, *, owners_only=False):
        if ctx.guild is None:
            await ctx.send("❌ Зөвхөн серверт ашиглана уу.", ephemeral=True)
            return False
        allowed = _is_bot_owner(self.bot, ctx.author.id) if owners_only else _can_manage(self.bot, ctx.guild, ctx.author)
        if not allowed:
            await ctx.send("⛔ Бот эзэмшигч/co-owner эрх шаардлагатай." if owners_only else "⛔ Админ эрх шаардлагатай.", ephemeral=True)
        return allowed

    @commands.hybrid_command(name="addxp", description="Хэрэглэгчид XP нэмэх (эзэмшигч/co-owner)")
    @commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="XP нэмэх хэрэглэгч", amount="Нэмэх XP тоо")
    async def addxp_cmd(self, ctx, user: discord.Member, amount: int):
        if not await self._authorize(ctx, owners_only=True):
            return
        if not 1 <= amount <= MAX_DB_INT:
            return await ctx.send("❌ Эерэг бүхэл XP оруулна уу.", ephemeral=True)
        engine = self._engine()
        if engine is None:
            return await ctx.send("❌ Leveling систем ачаалагдаагүй байна.", ephemeral=True)
        await ctx.defer(ephemeral=True)
        await engine.add_xp(user.id, ctx.guild.id, amount, member=user, check_mute=False)
        await ctx.send(f"✅ {user.display_name}-д {amount} XP нэмлээ.", ephemeral=True)

    @commands.hybrid_command(name="removexp", description="Хэрэглэгчээс XP хасах (эзэмшигч/co-owner)")
    @commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="XP хасах хэрэглэгч", amount="Хасах XP тоо")
    async def removexp_cmd(self, ctx, user: discord.Member, amount: int):
        if not await self._authorize(ctx, owners_only=True):
            return
        if not 1 <= amount <= MAX_DB_INT:
            return await ctx.send("❌ Эерэг бүхэл XP оруулна уу.", ephemeral=True)
        engine = self._engine()
        if engine is None:
            return await ctx.send("❌ Leveling систем ачаалагдаагүй байна.", ephemeral=True)
        await ctx.defer(ephemeral=True)
        await engine.remove_xp(user.id, ctx.guild.id, amount, member=user)
        await ctx.send(f"✅ {user.display_name}-ээс {amount} XP хасагдлаа.", ephemeral=True)

    @commands.hybrid_command(name="leveling_setup", aliases=["lsetup"], description="Түвшний системийн тохиргоо (админ)")
    @commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def leveling_setup(self, ctx):
        if not await self._authorize(ctx):
            return
        engine = self._engine()
        if engine is None:
            return await ctx.send("❌ Leveling систем ачаалагдаагүй байна.", ephemeral=True)
        await ctx.defer(ephemeral=True)
        view = LevelingSetupView(engine, ctx)
        embed = await view.build_embed()
        view.message = await ctx.send(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(LevelAdmin(bot))
