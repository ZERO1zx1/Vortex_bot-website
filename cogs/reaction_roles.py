"""Reaction roles — emoji дарж үүрэг авах/хасах систем.
Суулгах: 1) /rr setup дарж мессеж-үүргийн тохиргоо хийнэ
         2) Мессеж дээр дарсан emoji-оор уг үүргийг өгөх/хасах
Хадгалалт: Supabase reaction_roles хүснэгт (guild_id, message_id, emoji, role_id)
i18n: guild lang-аар embed хариу (t_direct)

v2.4.1 сайжруулалтууд:
- Setup message ID нь ✅ эмүү нэмсэн мессежээр зөв тогтоно (B1 fix)
- on_raw_reaction_remove нь ботын үйлдлийг шүүнэ (B2 fix)
- /rr action:remove emoji:😀 — нэг emoji устгах боломж (I3)
- Emoji normalization: custom emoji ID-ээр хадгалах (S3)
- Managed/position шалгалт setup үед (I5)
- Periodic cache refresh (I6)
"""
import json
from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
from utils.supabase_cog import SupabaseCog
from utils.i18n import t_direct, get_guild_lang, set_guild_lang
import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
from datetime import datetime, timezone

TABLE = "reaction_roles"


def normalize_emoji(emoji_raw: str) -> str:
    """Emoji-г нормчлох: custom emoji бол ID-ээр, unicode бол str.
    Custom emoji-г `<:name:id>` хэлбэрээс `<:name:id>` болгох (Discord API)."""
    raw = str(emoji_raw).strip()
    if raw.startswith("<a:") or raw.startswith("<:"):
        return raw  # custom emoji — ID агуулсан
    return raw


class RRSelectModal(ui.Modal, title="Reaction role нэмэх"):
    emoji = ui.TextInput(label="Emoji", placeholder="😀 (custom emoji copy/paste боломжтой)", max_length=60)
    role_id_str = ui.TextInput(label="Role ID", placeholder="Үүргийн ID", max_length=30)

    def __init__(self, cog, message_id: int):
        super().__init__()
        self.cog = cog
        self.message_id = message_id

    async def on_submit(self, interaction: discord.Interaction):
        emoji_raw = normalize_emoji(str(self.emoji.value))
        if not emoji_raw:
            return await interaction.response.send_message("❌ Emoji хоосон байна.", ephemeral=True)
        try:
            role_id = int(self.role_id_str.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Role ID тоо байх ёстой.", ephemeral=True)
        role = interaction.guild.get_role(role_id)
        if not role:
            return await interaction.response.send_message("❌ Ийм үүрэг олдсонгүй.", ephemeral=True)
        # Managed үүргийг (bots/integrations) reaction role-д өгөх боломжгүй (I5)
        if role.managed:
            return await interaction.response.send_message(
                "❌ Энэ үүрэг нь managed (бот/интеграцийн) үүрэг тул reaction role-д өгөх боломжгүй.",
                ephemeral=True)
        guild_id = interaction.guild.id
        exists = await self.cog.get_data(TABLE, {
            "guild_id": str(guild_id), "message_id": str(self.message_id), "emoji": emoji_raw})
        if exists:
            return await interaction.response.send_message("❌ Энэ мессеж дээр энэ emoji аль хэдийн ашиглагдаж байна.", ephemeral=True)
        await self.cog.update_data(TABLE, {
            "guild_id": str(guild_id), "message_id": str(self.message_id),
            "emoji": emoji_raw, "role_id": str(role_id),
            "created_at": datetime.now(timezone.utc).isoformat()})
        # ✅ эмүүг setup мессеж дээр нэмнэ (I4) — хэрэглэгч хаана дарж байгаагаа харах
        try:
            if interaction.message:
                await interaction.message.add_reaction("✅")
        except discord.HTTPException:
            pass
        self.cog.rebuild_cache(guild_id)
        lang = get_guild_lang(guild_id)
        embed = discord.Embed(title="✅ Reaction role нэмэгдлээ",
                              description=f"**{emoji_raw}** → {role.mention}", color=SUCCESS_COLOR)
        embed.set_footer(text=t_direct(lang, "rr.saved_hint"))
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RRListView(ui.View):
    def __init__(self, cog, guild_id: int):
        super().__init__(timeout=180)
        self.cog = cog
        self.guild_id = guild_id

    @discord.ui.button(label="🔄 Сэргээх", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._send_rr_list(interaction, self.guild_id, edit_existing=True)


class RRSetupView(ui.View):
    def __init__(self, cog, guild_id: int):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id
        self.message_id: int = None

    @discord.ui.button(label="📩 Мессеж бичих", style=discord.ButtonStyle.primary)
    async def send_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ✅ эмүү нэмсэн мессеж ID-г ашиглана — тодорхой харуулна (B1 fix)
        self.message_id = interaction.message.id
        try:
            await interaction.message.add_reaction("⬆️")
        except discord.HTTPException:
            pass
        await interaction.response.send_message("✅ Одоо **➕ Нэмэх** товч дээр дарж emoji + role тохируулаарай.\n"
                                                f"Бүх тохиргоог {interaction.channel.mention} сувгийн мессежид хадгаллаа.", ephemeral=True)

    @discord.ui.button(label="➕ Нэмэх", style=discord.ButtonStyle.success)
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.message_id is None:
            await interaction.response.send_message("❌ Эхлээд 📩 Мессеж бичих товч дарна уу.", ephemeral=True)
            return
        modal = RRSelectModal(self.cog, self.message_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🗑️ Бүгдийг устгах", style=discord.ButtonStyle.danger)
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.delete_data(TABLE, {"guild_id": str(self.guild_id)})
        self.cog.rebuild_cache(self.guild_id)
        lang = get_guild_lang(self.guild_id)
        await interaction.response.send_message(embed=discord.Embed(
            title="🗑️ Бүх reaction role устгагдлаа",
            description=t_direct(lang, "rr.cleared"), color=WARNING_COLOR), ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        ok = interaction.user.guild_permissions.manage_roles
        if not ok:
            await interaction.response.send_message("❌ Удирдах эрх (Manage Roles) хэрэгтэй.", ephemeral=True)
        return ok

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class ReactionRoles(SupabaseCog):
    """Reaction roles cog."""

    def __init__(self, bot):
        super().__init__(bot)
        self.cache: dict[int, dict] = {}  # guild_id -> {(msg_id, emoji): role_id}

    def rebuild_cache(self, guild_id: int):
        data = self.bot.db_manager.fetchall(TABLE, {"guild_id": str(guild_id)})
        self.cache[guild_id] = {(row["message_id"], row["emoji"]): int(row["role_id"]) for row in data}

    async def cog_load(self):
        await super().cog_load()
        await self.db.execute("sql", {"query": f"""
            CREATE TABLE IF NOT EXISTS {TABLE} (
                guild_id TEXT, message_id TEXT, emoji TEXT, role_id TEXT,
                created_at TEXT, PRIMARY KEY (guild_id, message_id, emoji))"""})
        for g in self.bot.guilds:
            self.rebuild_cache(g.id)
        self._cache_refresh.start()

    @tasks.loop(minutes=10)
    async def _cache_refresh(self):
        """Cache-ийг 10 мин тутам DB-ээс дахин уншина (I6)."""
        for g in self.bot.guilds:
            try:
                self.rebuild_cache(g.id)
            except Exception:
                pass

    async def cog_unload(self):
        self._cache_refresh.cancel()
        await super().cog_unload()

    # ══════════════ SETUP COMMANDS ══════════════
    @app_commands.command(name="rr", description="Reaction role тохиргоо")
    @app_commands.describe(action="Үйлдэл", emoji="Устгах emoji")
    @app_commands.choices(action=[
        app_commands.Choice(name="Setup (тохируулах)", value="setup"),
        app_commands.Choice(name="List (харуулах)", value="list"),
        app_commands.Choice(name="Remove (emoji устгах)", value="remove"),
    ])
    @commands.has_permissions(manage_roles=True)
    async def rr_setup(self, interaction: discord.Interaction, action: app_commands.Choice[str],
                       emoji: str = None):
        await interaction.response.defer(ephemeral=True)
        lang = get_guild_lang(interaction.guild.id)
        if action.value == "setup":
            await interaction.followup.send(
                embed=discord.Embed(title="🎯 Reaction role тохиргоо",
                                    description=t_direct(lang, "rr.setup_intro"), color=INFO_COLOR),
                view=RRSetupView(self, interaction.guild.id), ephemeral=True)
        elif action.value == "list":
            await self._send_rr_list(interaction, interaction.guild.id, edit_existing=False)
        else:  # remove
            if not emoji:
                return await interaction.followup.send(
                    embed=discord.Embed(title="❌ Emoji заана уу",
                                        description="`/rr action: Remove emoji:😀`", color=ERROR_COLOR),
                    ephemeral=True)
            emoji_raw = normalize_emoji(emoji)
            removed = await self.delete_data(TABLE, {
                "guild_id": str(interaction.guild.id), "emoji": emoji_raw})
            if not removed:
                return await interaction.followup.send(
                    embed=discord.Embed(title="❌ Олдсонгүй",
                                        description=f"**{emoji_raw}** emoji энэ серверт бүртгэгдээгүй.",
                                        color=ERROR_COLOR), ephemeral=True)
            self.rebuild_cache(interaction.guild.id)
            await interaction.followup.send(
                embed=discord.Embed(title="🗑️ Устгагдлаа",
                                    description=f"**{emoji_raw}** reaction role устгагдлаа.",
                                    color=WARNING_COLOR), ephemeral=True)

    @commands.hybrid_command(name="rrlist", description="Reaction role жагсаалт")
    async def rr_list(self, ctx: commands.Context):
        lang = get_guild_lang(ctx.guild.id)
        data = await self.get_all_data(TABLE, {"guild_id": str(ctx.guild.id)})
        if not data:
            return await ctx.send(embed=discord.Embed(
                title="🎯 Reaction roles", description=t_direct(lang, "rr.empty"), color=INFO_COLOR))
        desc = []
        for row in data:
            role = ctx.guild.get_role(int(row["role_id"]))
            if role:
                desc.append(f"{row['emoji']} → {role.mention}")
            else:
                desc.append(f"{row['emoji']} → `<@&{row['role_id']}>`")
        await ctx.send(embed=discord.Embed(
            title="🎯 Reaction roles", description="\n".join(desc), color=INFO_COLOR))

    async def _send_rr_list(self, interaction: discord.Interaction, guild_id: int, edit_existing: bool):
        lang = get_guild_lang(guild_id)
        data = await self.get_all_data(TABLE, {"guild_id": str(guild_id)})
        if not data:
            emb = discord.Embed(title="🎯 Reaction roles", description=t_direct(lang, "rr.empty"), color=INFO_COLOR)
        else:
            guild = self.bot.get_guild(guild_id)
            desc = [f"{row['emoji']} → <@&{row['role_id']}>" for row in data]
            emb = discord.Embed(title="🎯 Reaction roles", description="\n".join(desc), color=INFO_COLOR)
            emb.set_footer(text=t_direct(lang, "rr.footer_hint"))
        if edit_existing and interaction.message:
            await interaction.response.edit_message(embed=emb, view=None)
        else:
            await interaction.followup.send(embed=emb, view=RRListView(self, guild_id), ephemeral=True)

    # ══════════════ RAW REACTION HANDLER ══════════════
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if not payload.member or payload.member.bot:
            return
        guild_id = payload.guild_id
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        key = (str(payload.message_id), str(payload.emoji))
        roles = self.cache.get(guild_id, {})
        role_id = roles.get(key)
        if role_id is None:
            return
        role = guild.get_role(role_id)
        if not role:
            return
        try:
            if guild.me.top_role.position > role.position or guild.me.guild_permissions.administrator:
                await guild.get_member(payload.user_id).add_roles(role, reason="Reaction role")
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionRemoveEvent):
        # Ботын reaction устгах үйлдлийг шүүх (B2 fix)
        if payload.user_id == self.bot.user.id:
            return
        guild_id = payload.guild_id
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        key = (str(payload.message_id), str(payload.emoji))
        roles = self.cache.get(guild_id, {})
        role_id = roles.get(key)
        if role_id is None:
            return
        role = guild.get_role(role_id)
        if not role:
            return
        member = guild.get_member(payload.user_id)
        if member:
            try:
                await member.remove_roles(role, reason="Reaction role remove")
            except discord.HTTPException:
                pass

    # ══════════════ MESSAGE DELETE CLEANUP ══════════════
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if payload.guild_id is None:
            return
        guild_id = payload.guild_id
        data = await self.get_all_data(TABLE, {"guild_id": str(guild_id), "message_id": str(payload.message_id)})
        if data:
            await self.delete_data(TABLE, {"guild_id": str(guild_id), "message_id": str(payload.message_id)})
            self.rebuild_cache(guild_id)


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
