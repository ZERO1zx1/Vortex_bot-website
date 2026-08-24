import discord
from discord.ext import commands
import os
import sys
import time
import asyncio
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

from config_manager import load_config
from database.supabase_manager import SupabaseManager as DatabaseManager
from utils.branding import BOT_NAME, BOT_FOOTER
from utils.constants import DEFAULT_PREFIX

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ DISCORD_TOKEN not found! Check your .env file.")
    sys.exit(1)

config = load_config()

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
cogs_handler = RotatingFileHandler(
    LOG_DIR / "cogs.log",
    maxBytes=5 * 1024 * 1024,   # 5 MB per file
    backupCount=3,              # cogs.log.1 .. cogs.log.3
    encoding="utf-8",
)
cogs_handler.setLevel(logging.WARNING)  # WARNING+ бүгд файл руу
cogs_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
))

# TERMINAL LOG ТҮВШИН: config.json-ийн terminal_log_level-аар удирдагдана.
# "INFO"   → терминалд мэдээлэл л харагдана (алдаа файл руу)
# "WARNING"→ WARNING+ терминалд харагдана
# "ERROR"  → зөвхөн ERROR/CRITICAL
# "OFF"/"NONE" → терминалд огт лог бичигдэхгүй
LEVELS = {"DEBUG": logging.DEBUG, "INFO": logging.INFO,
          "WARNING": logging.WARNING, "ERROR": logging.ERROR,
          "CRITICAL": logging.CRITICAL}

class TerminalFilter(logging.Filter):
    def filter(self, record):
        return record.levelno < logging.WARNING

_term_level_name = str(config.get("terminal_log_level", "INFO")).strip().upper()
if _term_level_name in ("OFF", "NONE"):
    stream = logging.StreamHandler()
    stream.setLevel(logging.CRITICAL + 1)  # терминалд огт бичигдэхгүй
else:
    _term_level = LEVELS.get(_term_level_name, logging.INFO)
    stream = logging.StreamHandler()
    stream.setLevel(_term_level)
    # Алдаануудыг терминалд харуулахгүй файл руу л оруулах горимтой үед
    # WARNING-аас доош түвшнийг шүүх фильтрийг нэмнэ.
    if _term_level < logging.WARNING:
        stream.addFilter(TerminalFilter())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[stream, cogs_handler],
)
logger = logging.getLogger("aether")
logger.info("📟 Terminal log level: %s", _term_level_name)
# Файл хандлерыг ROOT logger-тэй холбох — бүх cog, discord,
# discord.ext-ийн WARNING+ алдаа бүгд ./logs/cogs.log руу бичигдэнэ.
cogs_handler.setLevel(logging.WARNING)

# Discord сангийн log-ыг WARNING+ болгох (INFO spam-аас зайлсхийх)
logging.getLogger("discord").setLevel(logging.WARNING)

# asyncio-ийн "Task exception was never retrieved" зэрэг дотоод логоос зайлсхийх
logging.getLogger("asyncio").setLevel(logging.WARNING)


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        intents.presences = True  # online/offline статус харахад шаардлагатай (Dev Portal-оос мөн асаана)

        prefix = config.get("prefix", DEFAULT_PREFIX)
        super().__init__(
            command_prefix=prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, replied_user=True),
        )

        self.db_manager = DatabaseManager()
        self.owner_ids = set()
        owner = config.get("owner_id")
        if owner:
            self.owner_ids.add(int(owner))
        for co in config.get("co_owner_ids", []):
            self.owner_ids.add(int(co))

        self.config = config
        self.loaded_cogs = []
        self.failed_cogs = []

    async def setup_hook(self):
        # Connect to Supabase
        try:
            self.db_manager.connect()
            logger.info("✅ Supabase connected")
        except Exception as e:
            logger.error("❌ Supabase connection error: %s", e)
            raise RuntimeError("Could not connect to Supabase") from e

        await self.db_manager.init_tables()

        # Load Cogs
        logger.info("📂 Loading Cogs...")
        cogs_to_load = [
            "admin", "avatar_check", "cafe", "carts", "confessions",
            "counting", "economy", "fun", "games", "giveaway",
            "help", "invite_tracker",             "level", "level_admin", "mafia", "mines",
            "lang", "moderation", "pvp", "roles", "shop", "stock",
            "stick", "marriage", "announcement", "tempvoice", "trade",
            "quests", "leaderboard", "casino", "greetings", "presence",
            "reaction_roles", "automod", "menu"
        ]

        for cog in cogs_to_load:
            start = time.perf_counter()
            try:
                logger.info("⏳ Loading %s.py...", cog)
                await asyncio.wait_for(
                    self.load_extension(f"cogs.{cog}"),
                    timeout=15,
                )
                elapsed = time.perf_counter() - start
                self.loaded_cogs.append(cog)
                logger.info("  ✅ %s.py loaded in %.2fs", cog, elapsed)
            except asyncio.TimeoutError:
                self.failed_cogs.append(cog)
                logger.error("  ❌ %s.py load timed out after 15s", cog)
            except Exception as e:
                self.failed_cogs.append(cog)
                logger.exception("  ❌ Error loading %s.py", cog)

        logger.info("📦 Cogs loaded: %d loaded, %d failed", len(self.loaded_cogs), len(self.failed_cogs))
        if self.failed_cogs:
            logger.warning("Failed cogs: %s", ", ".join(self.failed_cogs))

        # Sync Slash Commands
        try:
            synced = await self.tree.sync()
            logger.info("✅ %d slash commands synced.", len(synced))
        except Exception as e:
            logger.warning("⚠️ Slash command sync error: %s", e)

    async def on_command_error(self, ctx, error):
        """Text command алдааг ./logs/cogs.log руу бүртгэнэ."""
        if isinstance(error, commands.CommandNotFound):
            return  # танигдаагүй команд — файл хөлдөөхгүй

        # Hybrid командын дотоод алдааг задлах
        original = getattr(error, "original", None)
        if isinstance(error, commands.HybridCommandError) and original is not None:
            error = original

        # ---------- Хэрэглэгчийн оруулсан буруу өгөгдөл — эелдэг мессеж илгээж дуусгана ----------
        if isinstance(error, commands.MissingRequiredArgument):
            param = error.param.name
            await ctx.send(
                f"❌ Дутуу аргумент: `{param}` байхгүй байна.\n"
                f"💡 Зөв хэлбэр: `{ctx.prefix or ''}{ctx.command.qualified_name} <{param}>`",
                ephemeral=True,
            )
            return
        if isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
            await ctx.send(
                f"❌ Хэрэглэгч олдсонгүй: `{error.argument}`.\n"
                f"💡 Хэрэглэгчийг @mention эсвэл зөв ID-гаар дурдана уу.",
                ephemeral=True,
            )
            return
        if isinstance(error, commands.BadArgument):
            await ctx.send("❌ Аргументын формат буруу байна. Тусламжийг дахин шалгана уу.", ephemeral=True)
            return
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Хэтрүүлэн ашигласан тул {error.retry_after:.1f}с хүлээнэ үү.", ephemeral=True)
            return
        if isinstance(error, commands.MissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await ctx.send(f"⛔ Танд энэ командын эрх байхгүй: {perms}", ephemeral=True)
            return
        if isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await ctx.send(f"⛔ Надад энэ командын эрх байхгүй: {perms}", ephemeral=True)
            return
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ Энэ командыг зөвхөн серверт ашиглаж болно.", ephemeral=True)
            return
        if isinstance(error, commands.CheckFailure):
            await ctx.send("⛔ Та энэ командыг ашиглах эрхгүй байна.", ephemeral=True)
            return

        # Interaction хугацаа нь дууссан (Unknown interaction) — WARNING л болгох
        if isinstance(error, discord.NotFound) and "10062" in str(error):
            logger.warning("Interaction expired [%s] %s: %s", ctx.command, getattr(ctx.author, "id", "?"), error)
            return

        logger.exception("Command error [%s] %s: %s", ctx.command, ctx.author, error)

    async def on_app_command_error(self, interaction, error):
        """Slash command алдааг ./logs/cogs.log руу бүртгэнэ."""
        from discord import app_commands as _app

        cmd = interaction.command.qualified_name if interaction.command else "unknown"

        if isinstance(error, _app.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Хэтрүүлэн ашигласан тул {error.retry_after:.1f}с хүлээнэ үү.", ephemeral=True
            )
            return
        if isinstance(error, _app.MissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await interaction.response.send_message(f"⛔ Танд энэ командын эрх байхгүй: {perms}", ephemeral=True)
            return
        if isinstance(error, _app.CheckFailure):
            await interaction.response.send_message("⛔ Та энэ командыг ашиглах эрхгүй байна.", ephemeral=True)
            return
        if isinstance(error, (_app.TransformerError, _app.CommandInvokeError)):
            inner = getattr(error, "original", None)
            if isinstance(inner, discord.NotFound) and "10062" in str(inner):
                logger.warning("Interaction expired [%s] %s: %s", cmd, interaction.user, inner)
                return

        logger.exception("Slash error [%s] %s: %s", cmd, interaction.user, error)

    async def on_ready(self):
        logger.info("✅ %s is online!", self.user)
        logger.info("📊 Guilds: %d", len(self.guilds))
        # Presence is now managed by PresenceCog (rotating activities)
        # Website status heartbeat: ping Supabase every 60s
        # (add_loop нь commands.Bot-д байхгүй тул create_task ашиглана)
        # За давхар давтагдахаас сэргийлж task handle-г хадгална (reconnect-д дахин үүсгэхгүй)
        if getattr(self, "_heartbeat_task", None) is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        """Send a heartbeat to bot_status so the website shows the real Online/Offline state."""
        try:
            while not self.is_closed():
                try:
                    await self.db_manager.ping_bot("online")
                    logger.info("💓 Heartbeat sent (website status: Online)")
                except Exception:  # noqa: BLE001
                    logger.warning("⚠️ Failed to send heartbeat")
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass

    async def close(self):
        await self.db_manager.close()
        await super().close()


if __name__ == "__main__":
    bot = MyBot()
    try:
        bot.run(TOKEN, reconnect=True)
    except Exception as e:
        logger.exception("❌ Fatal error: %s", e)
        sys.exit(1)
