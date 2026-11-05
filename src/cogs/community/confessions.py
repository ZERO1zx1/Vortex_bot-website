import asyncio
import datetime
import logging

import discord
from discord import app_commands, ui
from discord.ext import commands

from src.core.exceptions import DatabaseSchemaError
from src.ui.setup import SetupPanel, SetupState, disable_setup_panel
from src.utils.config_cache import ConfigCache
from src.utils.constants import GOLD_COLOR, INFO_COLOR, WARNING_COLOR

logger = logging.getLogger(__name__)

CONFESSION_COLOR = 0x7C5CFC
CONFESSION_READY_COLOR = 0x57F287
MAX_CONFESSION_COOLDOWN = 86_400


def build_confession_start_embed(cfg: dict) -> discord.Embed:
    """Build the member-facing compose panel with the active privacy policy."""
    anonymous = bool(cfg.get("anonymity", True))
    cooldown = max(0, int(cfg.get("cooldown", 30) or 0))
    privacy = (
        "Таны нэр нийтлэгдэхгүй. Зөвхөн серверийн moderation бүртгэлд хадгалагдана."
        if anonymous
        else "Таны Discord нэр захианы доор харагдана."
    )
    embed = discord.Embed(
        title="✉️ Нууц захиа илгээх",
        description=(
            "Доорх **Захиа бичих** товчийг дарж гарчиг, агуулгаа оруулна уу. "
            "Илгээсний дараа зөвхөн танд баталгаажуулалт харагдана."
        ),
        color=CONFESSION_COLOR,
    )
    embed.add_field(name="Нууцлал", value=privacy, inline=False)
    embed.add_field(
        name="Дахин илгээх хугацаа",
        value="Хязгаарлалтгүй" if cooldown == 0 else f"{cooldown} секунд",
        inline=True,
    )
    embed.set_footer(text="Захиандаа хувийн мэдээлэл оруулахгүй байхыг зөвлөж байна.")
    return embed

# ==================== МОДАЛ: НУУЦ ЗАХИА ИЛГЭЭХ ====================
class ConfessionModal(ui.Modal, title="✉️ Нууц захиа бэлтгэх"):
    title_input = ui.TextInput(
        label="Гарчиг",
        placeholder="Жишээ: Надад хэлэх зүйл байна",
        max_length=100,
        required=True
    )
    content_input = ui.TextInput(
        label="Захиа",
        style=discord.TextStyle.paragraph,
        placeholder="Бодол, санал эсвэл түүхээ энд бичээрэй...",
        max_length=1500,
        required=True
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("❌ Сервер дотор ашиглана уу.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await self.cog.process_confession(
            user=interaction.user,
            guild=interaction.guild,
            content=f"**{self.title_input.value}**\n{self.content_input.value}",
            interaction=interaction
        )


class ConfessionStartView(ui.View):
    def __init__(self, cog, author_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.author_id = author_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.author_id:
            return True
        await interaction.response.send_message("⛔ Энэ confession panel өөр хэрэглэгчийнх.", ephemeral=True)
        return False

    @ui.button(label="Захиа бичих", emoji="✉️", style=discord.ButtonStyle.primary)
    async def open_modal(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ConfessionModal(self.cog))

    async def on_timeout(self):
        if self.message is None:
            return
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            logger.debug("Confession compose panel timeout edit failed", exc_info=True)

# ==================== МОДАЛ: КҮҮДАУН ТОХИРУУЛАХ ====================
class CooldownModal(ui.Modal, title="⏱️ Илгээх зай тохируулах"):
    seconds = ui.TextInput(
        label="Хүлээх хугацаа (секунд)",
        placeholder="0–86400",
        default="30",
        required=True
    )

    def __init__(self, view, current_value=30):
        super().__init__()
        self.view = view
        self.seconds.default = str(current_value)

    async def on_submit(self, interaction: discord.Interaction):
        if not await self.view.interaction_check(interaction):
            return
        try:
            cd = int(self.seconds.value)
        except ValueError:
            await interaction.response.send_message("❌ Зөвхөн тоо оруулна уу.", ephemeral=True)
            return
        if not 0 <= cd <= MAX_CONFESSION_COOLDOWN:
            await interaction.response.send_message(
                f"❌ 0–{MAX_CONFESSION_COOLDOWN} хооронд утга оруулна уу.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        await self.view.cog.update_config(self.view.guild_id, cooldown=cd)
        await self.view.refresh_panel(interaction.guild)
        value = "хязгаарлалтгүй" if cd == 0 else f"{cd} секунд"
        await interaction.followup.send(f"✅ Илгээх зай: **{value}**.", ephemeral=True)

# ==================== ТОХИРГООНЫ САМБАР (VIEW) ====================
class SetupView(ui.View):
    def __init__(self, cog, guild_id, author_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild_id != self.guild_id or interaction.guild is None:
            await interaction.response.send_message("❌ Энэ самбар өөр серверийнх байна.", ephemeral=True)
            return False
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Энэ самбар таных биш.", ephemeral=True)
            return False
        if not interaction.permissions.administrator:
            await interaction.response.send_message("❌ Админ эрх шаардлагатай.", ephemeral=True)
            return False
        return True

    async def refresh_panel(self, guild):
        if self.message is None:
            raise RuntimeError("setup panel message is not available")
        cfg = await self.cog.get_config(self.guild_id)
        embed = self.build_embed(cfg, guild)
        await self.message.edit(embed=embed, view=self)

    def build_embed(self, cfg, guild):
        cfg = cfg or {}
        input_id = cfg.get("confess_channel")
        output_id = cfg.get("output_channel")
        input_channel = guild.get_channel(input_id) if input_id else None
        output_channel = guild.get_channel(output_id) if output_id else None
        channel1 = input_channel.mention if input_channel else "Сонгоогүй"
        channel2 = output_channel.mention if output_channel else "Сонгоогүй"
        ready = input_channel is not None and output_channel is not None
        anonymous = bool(cfg.get("anonymity", True))
        cooldown = max(0, int(cfg.get("cooldown", 30) or 0))

        self.toggle_anon.label = "Нууцлал: асаалттай" if anonymous else "Нууцлал: унтраалттай"
        self.toggle_anon.style = (
            discord.ButtonStyle.success if anonymous else discord.ButtonStyle.secondary
        )
        self.cooldown_button.label = (
            "Илгээх зай: байхгүй" if cooldown == 0 else f"Илгээх зай: {cooldown} сек"
        )

        next_step = (
            "Өөрчлөлт бүр шууд хадгалагдана."
            if ready
            else "Доорх хоёр цэснээс оролт болон нийтлэх сувгаа сонгоно уу."
        )

        panel = SetupPanel(
            "Нууц захианы удирдлага",
            next_step,
            icon="✉️",
            state=SetupState.READY if ready else SetupState.INCOMPLETE,
            status="Ажиллахад бэлэн" if ready else "тохиргоо дутуу",
            color=CONFESSION_READY_COLOR if ready else CONFESSION_COLOR,
        )
        embed = panel.embed
        embed.add_field(
            name="Иргэд захиа бичих суваг",
            value=f"📥 {channel1}",
            inline=False,
        )
        embed.add_field(
            name="Захиа нийтлэгдэх суваг",
            value=f"📤 {channel2}",
            inline=False,
        )
        embed.add_field(
            name="Нэр харуулах",
            value="Үгүй — аноним" if anonymous else "Тийм — Discord нэртэй",
            inline=True,
        )
        embed.add_field(
            name="Илгээх зай",
            value="Хязгаарлалтгүй" if cooldown == 0 else f"{cooldown} секунд",
            inline=True,
        )
        return panel.finish("Самбар 10 минут идэвхтэй • Зөвхөн нээсэн админ удирдана")

    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📥 Нууц захианы суваг сонго...", min_values=1, max_values=1, row=0)
    async def select_confess_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        await interaction.response.defer()
        channel = select.values[0]
        await self.cog.update_config(self.guild_id, confess_channel_id=channel.id)
        cfg = await self.cog.get_config(self.guild_id)
        await interaction.edit_original_response(
            embed=self.build_embed(cfg, interaction.guild), view=self
        )

    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📤 Гаралтын суваг сонго...", min_values=1, max_values=1, row=1)
    async def select_output_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        await interaction.response.defer()
        channel = select.values[0]
        await self.cog.update_config(self.guild_id, output_channel_id=channel.id)
        cfg = await self.cog.get_config(self.guild_id)
        await interaction.edit_original_response(
            embed=self.build_embed(cfg, interaction.guild), view=self
        )

    @ui.button(label="Нууцлал: асаалттай", emoji="🔒", style=discord.ButtonStyle.success, row=2)
    async def toggle_anon(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        cfg = await self.cog.get_config(self.guild_id)
        if cfg is None:
            await interaction.followup.send(
                "❌ Эхлээд сувгуудыг сонгоно уу.", ephemeral=True
            )
            return
        new_state = not cfg['anonymity']
        await self.cog.update_config(self.guild_id, anonymity=new_state)
        cfg = await self.cog.get_config(self.guild_id)
        await interaction.edit_original_response(
            embed=self.build_embed(cfg, interaction.guild), view=self
        )

    @ui.button(label="Илгээх зай: 30 сек", emoji="⏱️", style=discord.ButtonStyle.secondary, row=2)
    async def cooldown_button(self, interaction: discord.Interaction, button: ui.Button):
        cfg = await self.cog.get_config(self.guild_id)
        current = (cfg or {}).get("cooldown", 30)
        await interaction.response.send_modal(CooldownModal(self, current))

    @ui.button(label="Дахин ачаалах", emoji="↻", style=discord.ButtonStyle.gray, row=2)
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        cfg = await self.cog.get_config(self.guild_id)
        await interaction.edit_original_response(
            embed=self.build_embed(cfg, interaction.guild), view=self
        )

    async def on_timeout(self):
        await disable_setup_panel(self, self.message)

# ==================== ҮНДСЭН COG ====================
class Confessions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._cfg_cache = ConfigCache(ttl=15.0, name="confession_config")
        self._blacklist_cache = ConfigCache(ttl=30.0, name="confession_blacklist")

    # ----- DB туслахууд -----
    async def get_config(self, guild_id):

        async def _load():
            # fetch_safe swallows PGRST202/PGRST205/404/42501 so a DB setup problem
            # returns None (unconfigured) instead of breaking every message.
            row = await self.bot.db_manager.fetch_safe(
                "confession_config", {"guild_id": str(guild_id)}, single=True
            )
            if not row:
                return None
            return {
                "confess_channel": int(row["confess_channel_id"]) if row.get("confess_channel_id") else None,
                "output_channel": int(row["output_channel_id"]) if row.get("output_channel_id") else None,
                "anonymity": bool(row.get("anonymity", 1)),
                "cooldown": row.get("cooldown", 30),
                "next_id": row.get("next_id", 1)
            }

        return await self._cfg_cache.get(guild_id, _load)

    async def get_blacklist(self, guild_id):
        async def _load():
            rows = await self.bot.db_manager.fetch_all(
                "confession_blacklist", {"guild_id": str(guild_id)}
            )
            return tuple(
                word
                for row in rows
                if (word := str(row.get("word", "")).strip().lower())
            )

        return await self._blacklist_cache.get(guild_id, _load)

    async def update_config(self, guild_id, **kwargs):
        data = {"guild_id": str(guild_id)}
        data.update(kwargs)
        await self.bot.db_manager.upsert("confession_config", data, on_conflict="guild_id")
        self._cfg_cache.invalidate(guild_id)

    async def increment_id(self, guild_id):
        guild_id = str(guild_id)
        try:
            response = await self.bot.db_manager.rpc(
                "allocate_confession_id", {"p_guild_id": guild_id}
            )
        except DatabaseSchemaError:
            # Existing deployments may briefly run new code before migration
            # 004 is applied. Use an atomic compare-and-swap on next_id so
            # confession numbering remains available and unique across bot
            # processes instead of failing every message with PGRST202.
            for _ in range(8):
                row = await self.bot.db_manager.fetch_one(
                    "confession_config", {"guild_id": guild_id}, selects="next_id"
                )
                if not row:
                    raise RuntimeError(f"confession config not found for guild {guild_id}")
                allocated = int(row.get("next_id") or 1)
                updated = await self.bot.db_manager.update(
                    "confession_config",
                    {"guild_id": guild_id, "next_id": allocated},
                    {"next_id": allocated + 1},
                )
                if updated:
                    self._cfg_cache.invalidate(guild_id)
                    return allocated
                await asyncio.sleep(0)
            raise RuntimeError(
                f"could not allocate confession id for guild {guild_id} after contention"
            )
        data = getattr(response, "data", response)
        if isinstance(data, list):
            allocated = data[0] if data else None
        else:
            allocated = data
        if isinstance(allocated, dict):
            allocated = allocated.get("allocate_confession_id")
        if allocated is None:
            raise RuntimeError("allocate_confession_id returned no value")
        self._cfg_cache.invalidate(guild_id)
        return int(allocated)

    # ----- ГОЛ БОЛОВСРУУЛАЛТ -----
    async def process_confession(self, user, guild, content, interaction=None):
        cfg = await self.get_config(guild.id)
        if not cfg:
            if interaction:
                await interaction.followup.send("❌ Систем тохируулагдаагүй. `/confess_setup`-ээр тохируулна уу.", ephemeral=True)
            return

        now = int(datetime.datetime.now(datetime.UTC).timestamp())
        # Күүдаун шалгах
        cd_row = await self.bot.db_manager.fetch_one(
            "confession_cooldown", {"user_id": str(user.id), "guild_id": str(guild.id)}
        )
        last_time = cd_row.get("last_time", 0) if cd_row else 0
        if last_time and now - last_time < cfg["cooldown"]:
            remaining = cfg["cooldown"] - (now - last_time)
            msg = f"⏳ Та {remaining} секундын дараа дахин илгээх боломжтой."
            if interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                try:
                    await user.send(msg)
                except discord.HTTPException:
                    logger.debug("Confession cooldown DM failed for user %s", user.id, exc_info=True)
            return

        # Хар жагсаалт шалгах
        blacklist = await self.get_blacklist(guild.id)
        for w in blacklist:
            if w in content.lower():
                msg = "🚫 Таны захиа хориотой үг агуулж байна."
                if interaction:
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    try:
                        await user.send(msg)
                    except discord.HTTPException:
                        logger.debug("Confession rejection DM failed for user %s", user.id, exc_info=True)
                return

        # Гаралтын сувагт илгээх
        output_channel = guild.get_channel(cfg["output_channel"])
        if not output_channel:
            if interaction:
                await interaction.followup.send("❌ Гаралтын суваг олдсонгүй.", ephemeral=True)
            return

        # ID авах
        confess_id = await self.increment_id(guild.id)

        author_name = "Anonymous" if cfg["anonymity"] else user.display_name
        embed = discord.Embed(
            title=f"📩 Confession #{confess_id}",
            description=content,
            color=GOLD_COLOR,
            timestamp=datetime.datetime.now(datetime.UTC)
        )
        embed.set_footer(text=f"Илгээсэн: {author_name}")

        sent_msg = await output_channel.send(embed=embed)

        # Күүдаун бүртгэх + түүх хадгалах
        await self.bot.db_manager.insert("confession_messages", {
            "guild_id": str(guild.id),
            "confession_id": confess_id,
            "message_id": str(sent_msg.id),
            "user_id": str(user.id),
            "content": content[:500],
        })
        await self.bot.db_manager.upsert(
            "confession_cooldown",
            {"user_id": str(user.id), "guild_id": str(guild.id), "last_time": now},
            on_conflict="user_id,guild_id",
        )

        # Даалгаврын системд мэдэгдэх
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            await quests_cog.trigger_event(user.id, guild.id, "confession_write", 1)

        # Хэрэглэгчид амжилттай илгээсэн тухай мэдэгдэх
        if interaction:
            await interaction.followup.send(f"✅ Таны нууц захиа (#{confess_id}) амжилттай илгээгдлээ.", ephemeral=True)
        else:
            try:
                await user.send(f"✅ Таны нууц захиа (#{confess_id}) амжилттай илгээгдлээ.")
            except discord.HTTPException:
                logger.debug("Confession confirmation DM failed for user %s", user.id, exc_info=True)

    # ----- USER PREFIX COMMANDS -----
    @commands.command(name="confess")
    async def confess_command(self, ctx):
        if ctx.guild is None:
            return await ctx.send("❌ Сервер дотор ашиглана уу.")
        cfg = await self.get_config(ctx.guild.id)
        if not cfg:
            return await ctx.send("❌ Систем тохируулаагүй. Админ `confess_setup`-ээр тохируулна уу.")
        view = ConfessionStartView(self, ctx.author.id)
        view.message = await ctx.send(embed=build_confession_start_embed(cfg), view=view)

    @app_commands.command(name="confess_setup", description="Нууц захианы тохиргооны самбар нээх")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def confess_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg = await self.get_config(interaction.guild_id)
        view = SetupView(self, interaction.guild_id, interaction.user.id)
        embed = view.build_embed(cfg, interaction.guild)
        view.message = await interaction.followup.send(embed=embed, view=view, ephemeral=True, wait=True)

    @app_commands.command(name="confess_blacklist", description="Хориотой үг удирдах")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def confess_blacklist(
        self,
        interaction: discord.Interaction,
        action: str,
        word: str | None = None,
    ):
        await interaction.response.defer(ephemeral=True)
        if action.lower() == "add":
            if not word:
                return await interaction.followup.send("❌ Үг оруулна уу.", ephemeral=True)
            await self.bot.db_manager.upsert(
                "confession_blacklist",
                {"guild_id": str(interaction.guild_id), "word": word.lower()},
                on_conflict="guild_id,word",
            )
            self._blacklist_cache.invalidate(interaction.guild_id)
            await interaction.followup.send(f"✅ `{word}` хар жагсаалтад нэмэгдлээ.", ephemeral=True)
        elif action.lower() == "remove":
            if not word:
                return await interaction.followup.send("❌ Үг оруулна уу.", ephemeral=True)
            await self.bot.db_manager.delete(
                "confession_blacklist",
                {"guild_id": str(interaction.guild_id), "word": word.lower()},
            )
            self._blacklist_cache.invalidate(interaction.guild_id)
            await interaction.followup.send(f"✅ `{word}` хар жагсаалтаас хасагдлаа.", ephemeral=True)
        elif action.lower() == "list":
            rows = await self.bot.db_manager.fetch_all(
                "confession_blacklist", {"guild_id": str(interaction.guild_id)}
            )
            if not rows:
                await interaction.followup.send("📭 Хориотой үг байхгүй.", ephemeral=True)
            else:
                words = ", ".join([f"`{r.get('word', '')}`" for r in rows])
                await interaction.followup.send(f"🚫 Хориотой үгс: {words}", ephemeral=True)
        else:
            await interaction.followup.send("❌ `add`, `remove`, `list` сонголтыг ашиглана уу.", ephemeral=True)

    @app_commands.command(name="confess_delete", description="Нууц захиаг устгах (админ)")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def confess_delete(self, interaction: discord.Interaction, confession_id: int):
        await interaction.response.defer(ephemeral=True)
        cfg = await self.get_config(interaction.guild_id)
        if not cfg:
            return await interaction.followup.send("❌ Систем тохируулагдаагүй.", ephemeral=True)
        msg_row = await self.bot.db_manager.fetch_one(
            "confession_messages",
            {"guild_id": str(interaction.guild_id), "confession_id": confession_id},
        )
        if not msg_row:
            return await interaction.followup.send(f"❌ #{confession_id} олдсонгүй.", ephemeral=True)
        msg_id = int(msg_row["message_id"])
        content = msg_row.get("content", "")
        channel = interaction.guild.get_channel(cfg["output_channel"])
        if channel is None:
            return await interaction.followup.send("❌ Гаралтын суваг олдсонгүй. Бүртгэлийг устгаагүй.", ephemeral=True)
        try:
            msg = await channel.fetch_message(msg_id)
            await msg.delete()
        except discord.NotFound:
            # Older records have no source channel. A changed output channel
            # makes NotFound ambiguous; retain history instead of claiming
            # deletion of a message that may still exist in the old channel.
            return await interaction.followup.send(
                "❌ Захиа одоогийн гаралтын сувагт олдсонгүй. Хуучин сувгийг шалгана уу; бүртгэлийг хадгалсан.",
                ephemeral=True,
            )
        except discord.HTTPException:
            logger.warning("Confession deletion failed for message %s", msg_id, exc_info=True)
            return await interaction.followup.send("❌ Discord захиаг устгаж чадсангүй. Бүртгэлийг хадгалсан; дахин оролдоно уу.", ephemeral=True)
        await self.bot.db_manager.delete(
            "confession_messages",
            {"guild_id": str(interaction.guild_id), "confession_id": confession_id},
        )
        embed = discord.Embed(title="🗑️ Захиа устгагдлаа",
                              description=f"Захиа #{confession_id} устгагдсан.\nАгуулга: {content[:100]}...",
                              color=WARNING_COLOR)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @commands.command(name="confess_stats")
    @commands.guild_only()
    async def confess_stats(self, ctx: commands.Context):
        cfg = await self.get_config(ctx.guild.id)
        if not cfg:
            return await ctx.send("❌ Систем тохируулагдаагүй.")
        cooldown_rows = await self.bot.db_manager.fetch_all(
            "confession_cooldown", {"guild_id": str(ctx.guild.id)}
        )
        now = int(datetime.datetime.now(datetime.UTC).timestamp())
        active = sum(
            1 for row in cooldown_rows
            if row.get("last_time") and now - int(row["last_time"]) < cfg["cooldown"]
        )
        msg_rows = await self.bot.db_manager.fetch_all(
            "confession_messages", {"guild_id": str(ctx.guild.id)}
        )
        total_msgs = len(msg_rows)
        embed = discord.Embed(
            title="📊 Нууц захианы статистик",
            color=INFO_COLOR,
            description=f"**Одоогоор хадгалагдсан:** {total_msgs}\n**Хамгийн сүүлд олгосон ID:** {cfg['next_id'] - 1}\n**Идэвхтэй күүдаун:** {active}\n**Аноним:** {'Идэвхтэй' if cfg['anonymity'] else 'Унтарсан'}\n**Күүдаун:** {cfg['cooldown']}s"
        )
        await ctx.send(embed=embed)

    # ----- СУВГАНЫ СОНСГОЛ -----
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        cfg = await self.get_config(message.guild.id)
        if not cfg or message.channel.id != cfg.get("confess_channel"):
            return
        try:
            await self.process_confession(user=message.author, guild=message.guild, content=message.content)
        except Exception as exc:
            # Protect against transient DB failures mid-process without
            # leaking a full traceback for every single guild message.
            if getattr(exc, "code", None) in ("42501", "PGRST202", "PGRST205"):
                logger.debug(
                    "confession DB unavailable in guild %s: %s",
                    message.guild.id, exc, exc_info=True,
                )
            else:
                logger.warning("confession error in guild %s", message.guild.id, exc_info=True)
            # Do not destroy the original submission when delivery/storage
            # fails: keep it available for recovery, without logging its text.
            return
        try:
            await message.delete()
        except discord.HTTPException:
            logger.warning("Confession source message deletion failed", exc_info=True)

    async def cog_load(self):
        # Tables are pre-configured in Supabase via SQL migrations
        pass

async def setup(bot):
    await bot.add_cog(Confessions(bot))
