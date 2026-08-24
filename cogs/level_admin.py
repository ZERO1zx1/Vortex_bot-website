import logging
from typing import Optional

import discord
from discord.ext import commands, tasks
from discord import ui, app_commands

from utils.branding import BOT_NAME
from utils.supabase_cog import SupabaseCog

from cogs.level import (
    Leveling, get_config, set_config, GOLD_COLOR, INFO_COLOR, ERROR_COLOR,
)

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# UI VIEWS — эдгээр нь үндсэн "Leveling" когийг (engine) ашиглана
# ═══════════════════════════════════════════════════════════════════════════════

class LevelRewardManagerView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=600)
        self.cog = cog; self.ctx = ctx; self.selected_level = None
    async def build_embed(self):
        entries = await self.cog.get_level_rewards(self.ctx.guild.id)
        embed = discord.Embed(title="🎁 Түвшний мөнгөн шагнал", color=GOLD_COLOR)
        if not entries: embed.description = "Одоогоор ямар ч шагнал тохируулаагүй байна."
        else:
            lines = []
            for e in entries: lines.append(f"**Level {e['level']}** → {e['money']:,} ₮")
            embed.description = "\n".join(lines)
        embed.set_footer(text="Доорх цэсээр түвшин сонгоод 'Шагнал тохируулах' эсвэл 'Устгах' дарна уу.")
        return embed
    async def refresh_message(self, interaction):
        embed = await self.build_embed()
        await interaction.edit_original_response(embed=embed, view=self)
    @ui.select(placeholder="Түвшин сонгох", row=0, min_values=1, max_values=1)
    async def level_select(self, interaction, select):
        self.selected_level = int(select.values[0])
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"Түвшин {self.selected_level} сонгогдлоо.", ephemeral=True)
    @ui.button(label="💰 Шагнал тохируулах", style=discord.ButtonStyle.green, row=1)
    async def set_reward_btn(self, interaction, button):
        if self.selected_level is None: return await interaction.response.send_message("❌ Эхлээд түвшин сонгоно уу.", ephemeral=True)
        modal = ui.Modal(title="Шагнал тохируулах")
        money_input = ui.TextInput(label="Мөнгөн дүн (₮)", placeholder="5000", required=True)
        modal.add_item(money_input)
        async def on_submit(inter):
            try:
                money = int(money_input.value)
                if money <= 0: raise ValueError
            except: return await inter.response.send_message("❌ Эерэг бүхэл тоо оруулна уу.", ephemeral=True)
            await self.cog.set_level_reward(self.ctx.guild.id, self.selected_level, money)
            await inter.response.send_message(f"✅ Level {self.selected_level} → {money:,} ₮ тохируулагдлаа.", ephemeral=True)
            await self.refresh_message(inter)
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)
    @ui.button(label="🗑️ Устгах", style=discord.ButtonStyle.red, row=1)
    async def remove_reward_btn(self, interaction, button):
        if self.selected_level is None: return await interaction.response.send_message("❌ Эхлээд түвшин сонгоно уу.", ephemeral=True)
        await self.cog.delete_level_reward(self.ctx.guild.id, self.selected_level)
        await interaction.response.send_message(f"🗑️ Level {self.selected_level} шагнал устгагдлаа.", ephemeral=True)
        await self.refresh_message(interaction)


class LevelRoleManagerView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=600)
        self.cog = cog; self.ctx = ctx
        self.selected_level = None; self.selected_role = None
    async def build_embed(self):
        entries = await self.cog.get_level_roles(self.ctx.guild.id)
        embed = discord.Embed(title="🛠️ Түвшний ролиудыг тохируулах", color=INFO_COLOR)
        if not entries: embed.description = "Одоогоор ямар ч түвшний роль тохируулаагүй байна."
        else:
            lines = []
            for e in entries:
                role = self.ctx.guild.get_role(e["role_id"])
                role_text = role.mention if role else f"<@&{e['role_id']}>"
                lines.append(f"**Level {e['level']}** → {role_text}")
            embed.description = "\n".join(lines)
        embed.set_footer(text="Доорх цэсээр түвшин/роль сонгоод 'Тохируулах' эсвэл 'Устгах' дарна уу.")
        return embed
    async def refresh_message(self, interaction):
        embed = await self.build_embed()
        await interaction.edit_original_response(embed=embed, view=self)
    @ui.select(placeholder="1️⃣ Түвшин сонгох", row=0, min_values=1, max_values=1)
    async def level_select(self, interaction, select):
        self.selected_level = int(select.values[0])
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"Түвшин {self.selected_level} сонгогдлоо.", ephemeral=True)
    @ui.select(cls=ui.RoleSelect, placeholder="2️⃣ Роль сонгох", row=1, min_values=1, max_values=1)
    async def role_select(self, interaction, select):
        self.selected_role = select.values[0]
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"Роль {self.selected_role.mention} сонгогдлоо.", ephemeral=True)
    @ui.button(label="✅ Тохируулах", style=discord.ButtonStyle.green, row=2)
    async def set_btn(self, interaction, button):
        if self.selected_level is None or self.selected_role is None:
            return await interaction.response.send_message("❌ Түвшин болон роль сонгоно уу.", ephemeral=True)
        await self.cog.set_level_role(self.ctx.guild.id, self.selected_level, self.selected_role.id)
        await interaction.response.send_message(f"✅ Level {self.selected_level} → {self.selected_role.mention}", ephemeral=True)
        await self.refresh_message(interaction)
    @ui.button(label="🗑️ Устгах", style=discord.ButtonStyle.red, row=2)
    async def remove_btn(self, interaction, button):
        if self.selected_level is None: return await interaction.response.send_message("❌ Түвшин сонгоно уу.", ephemeral=True)
        await self.cog.delete_level_role(self.ctx.guild.id, self.selected_level)
        await interaction.response.send_message(f"🗑️ Level {self.selected_level} устгагдлаа.", ephemeral=True)
        await self.refresh_message(interaction)
    @ui.button(label="🎁 Шагнал", style=discord.ButtonStyle.blurple, row=3)
    async def reward_btn(self, interaction, button):
        view = LevelRewardManagerView(self.cog, self.ctx)
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)


class LevelingSetupView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=600)
        self.cog = cog; self.ctx = ctx; self.message = None
    async def interaction_check(self, interaction):
        if interaction.user.id == interaction.guild.owner_id or interaction.user.id in self.cog.bot.config.get("co_owner_ids",[]): return True
        await interaction.response.send_message("⛔ Сервер эзэмшигч эсвэл ботын co-owner эрх шаардлагатай.", ephemeral=True)
        return False
    async def refresh(self):
        cfg = await get_config(self.cog.bot.db_manager, self.ctx.guild.id)
        embed = discord.Embed(title="🔧 Түвшний систем тохиргоо", color=INFO_COLOR)
        ch = self.ctx.guild.get_channel(cfg["announce_channel"]) if cfg["announce_channel"] else None
        embed.add_field(name="📢 Мэдэгдэл суваг", value=ch.mention if ch else "Тохируулаагүй", inline=False)
        embed.add_field(name="Систем идэвхтэй", value="✅" if cfg["enabled"] else "❌", inline=True)
        embed.add_field(name="Дуут XP", value="✅" if cfg["voice_xp_enabled"] else "❌", inline=True)
        embed.add_field(name="Cooldown (msg/react)", value=f"{cfg['msg_cooldown']}с / {cfg['react_cooldown']}с", inline=True)
        embed.add_field(name="Прогресс", value=f"{cfg['prog_type']} (base={cfg['prog_base']}, step={cfg['prog_step']})", inline=True)
        embed.add_field(name="Урилгын XP", value=str(cfg.get("invite_xp",0)), inline=True)
        embed.add_field(name="Гэрлэлтийн урамшуулал", value=f"{cfg.get('marriage_bonus',0.1)*100}%", inline=True)
        await self.message.edit(embed=embed, view=self)
    @ui.button(label="📢 Суваг сонгох", style=discord.ButtonStyle.secondary, row=0)
    async def channel_btn(self, interaction, button):
        opts = []
        for ch in interaction.guild.text_channels[:25]:
            opts.append(discord.SelectOption(label=f"#{ch.name}", value=str(ch.id)))
        if not opts: return await interaction.response.send_message("Сонгох суваг байхгүй.", ephemeral=True)
        class ChannelSelect(ui.Select):
            def __init__(self): super().__init__(placeholder="Мэдэгдэл сувгаа сонго...", options=opts)
            async def callback(self, inter):
                cfg = await get_config(self.view.cog.bot.db_manager, self.view.ctx.guild.id)
                cfg["announce_channel"] = int(self.values[0])
                await set_config(self.view.cog.bot.db_manager, self.view.ctx.guild.id, cfg)
                await inter.response.send_message("✅ Суваг тохируулагдлаа.", ephemeral=True)
                await self.view.refresh()
        view = ui.View(timeout=60); view.add_item(ChannelSelect())
        await interaction.response.send_message("Сувгаа сонгоно уу:", view=view, ephemeral=True)
    @ui.button(label="🔄 Систем унтраах/асаах", style=discord.ButtonStyle.primary, row=0)
    async def toggle_btn(self, interaction, button):
        cfg = await get_config(self.cog.bot.db_manager, self.ctx.guild.id)
        cfg["enabled"] = not cfg["enabled"]
        await set_config(self.cog.bot.db_manager, self.ctx.guild.id, cfg)
        await interaction.response.send_message(f"Систем {'ассан' if cfg['enabled'] else 'унтарсан'}.", ephemeral=True)
        await self.refresh()
    @ui.button(label="⏱ Cooldown тохируулах", style=discord.ButtonStyle.secondary, row=1)
    async def cd_btn(self, interaction, button):
        modal = ui.Modal(title="Cooldown (секунд)")
        msg_inp = ui.TextInput(label="Мессеж", placeholder="60", required=True)
        react_inp = ui.TextInput(label="Реакц", placeholder="10", required=True)
        modal.add_item(msg_inp); modal.add_item(react_inp)
        async def on_submit(inter):
            try:
                m = int(msg_inp.value); r = int(react_inp.value)
                if m<=0 or r<=0: raise ValueError
            except: return await inter.response.send_message("❌ Эерэг бүхэл тоо оруулна уу.", ephemeral=True)
            cfg = await get_config(self.cog.bot.db_manager, self.ctx.guild.id)
            cfg["msg_cooldown"] = m; cfg["react_cooldown"] = r
            await set_config(self.cog.bot.db_manager, self.ctx.guild.id, cfg)
            await inter.response.send_message("✅ Cooldown шинэчлэгдлээ.", ephemeral=True)
            await self.refresh()
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)
    @ui.button(label="🎨 Арын зураг URL", style=discord.ButtonStyle.secondary, row=1)
    async def bg_btn(self, interaction, button):
        modal = ui.Modal(title="Арын зураг")
        url_inp = ui.TextInput(label="Зургийн URL", placeholder="https://...", required=True)
        modal.add_item(url_inp)
        async def on_submit(inter):
            cfg = await get_config(self.cog.bot.db_manager, self.ctx.guild.id)
            cfg["background_url"] = url_inp.value.strip()
            await set_config(self.cog.bot.db_manager, self.ctx.guild.id, cfg)
            await inter.response.send_message("✅ Арын зураг тохируулагдлаа.", ephemeral=True)
            await self.refresh()
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)
    @ui.button(label="🎖️ Түвшний роль тохиргоо", style=discord.ButtonStyle.success, row=2)
    async def role_manager_btn(self, interaction, button):
        view = LevelRoleManagerView(self.cog, self.ctx)
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN COG
# ═══════════════════════════════════════════════════════════════════════════════
class LevelAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _is_allowed(self, user):
        try:
            cfg = self.bot.config
            return user.id == cfg.get("owner_id") or user.id in cfg.get("co_owner_ids", [])
        except: return False

    def _engine(self) -> Optional[Leveling]:
        return self.bot.get_cog("Leveling")

    # ── /addxp ──
    @commands.hybrid_command(name="addxp", description="Хэрэглэгчид XP нэмэх (эзэмшигч/co-owner)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="XP нэмэх хэрэглэгч", amount="Нэмэх XP тоо")
    async def addxp_cmd(self, ctx, user: discord.Member, amount: int):
        if not self._is_allowed(ctx.author):
            return await ctx.send("⛔ Зөвхөн бот эзэмшигч эсвэл co-owner ашиглах боломжтой.", ephemeral=True)
        if amount <= 0:
            return await ctx.send("❌ Эерэг тоо оруулна уу.", ephemeral=True)
        engine = self._engine()
        if not engine:
            return await ctx.send("❌ Leveling систем ачаалагдаагүй байна.", ephemeral=True)
        await engine._add_xp(user.id, ctx.guild.id, amount, member=user, check_mute=False)
        await ctx.send(f"✅ {user.display_name}-д {amount} XP нэмлээ.")

    # ── /removexp ──
    @commands.hybrid_command(name="removexp", description="Хэрэглэгчээс XP хасах (эзэмшигч/co-owner)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="XP хасах хэрэглэгч", amount="Хасах XP тоо")
    async def removexp_cmd(self, ctx, user: discord.Member, amount: int):
        if not self._is_allowed(ctx.author):
            return await ctx.send("⛔ Зөвхөн бот эзэмшигч эсвэл co-owner ашиглах боломжтой.", ephemeral=True)
        if amount <= 0:
            return await ctx.send("❌ Эерэг тоо оруулна уу.", ephemeral=True)
        engine = self._engine()
        if not engine:
            return await ctx.send("❌ Leveling систем ачаалагдаагүй байна.", ephemeral=True)
        await engine._add_xp(user.id, ctx.guild.id, -amount, member=user, check_mute=False)
        await ctx.send(f"✅ {user.display_name}-ээс {amount} XP хасагдлаа.")

    # ── /leveling_setup ──
    @commands.hybrid_command(name="leveling_setup", aliases=["lsetup"], description="Түвшний системийн тохиргоо (админ)")
    @app_commands.default_permissions(administrator=True)
    async def leveling_setup(self, ctx):
        if not (ctx.author.guild_permissions.administrator or self._is_allowed(ctx.author)):
            return await ctx.send("⛔ Админ эрх шаардлагатай.", ephemeral=True)
        engine = self._engine()
        if not engine:
            return await ctx.send("❌ Leveling систем ачаалагдаагүй байна.", ephemeral=True)
        cfg = await get_config(self.bot.db_manager, ctx.guild.id)
        embed = discord.Embed(title="🔧 Түвшний систем тохиргоо", color=INFO_COLOR)
        ch = ctx.guild.get_channel(cfg["announce_channel"]) if cfg["announce_channel"] else None
        embed.add_field(name="📢 Мэдэгдэл суваг", value=ch.mention if ch else "Тохируулаагүй", inline=False)
        embed.add_field(name="Систем идэвхтэй", value="✅" if cfg["enabled"] else "❌", inline=True)
        embed.add_field(name="Дуут XP", value="✅" if cfg["voice_xp_enabled"] else "❌", inline=True)
        embed.add_field(name="Cooldown (msg/react)", value=f"{cfg['msg_cooldown']}с / {cfg['react_cooldown']}с", inline=True)
        embed.add_field(name="Прогресс", value=f"{cfg['prog_type']} (base={cfg['prog_base']}, step={cfg['prog_step']})", inline=True)
        embed.add_field(name="Урилгын XP", value=str(cfg.get("invite_xp",0)), inline=True)
        embed.add_field(name="Гэрлэлтийн урамшуулал", value=f"{cfg.get('marriage_bonus',0.1)*100}%", inline=True)
        view = LevelingSetupView(engine, ctx)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg


async def setup(bot):
    await bot.add_cog(LevelAdmin(bot))
