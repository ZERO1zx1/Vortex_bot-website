import discord
from discord.ext import commands
import os
import sys
import logging
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aether")


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True

        prefix = config.get("prefix", DEFAULT_PREFIX)
        super().__init__(command_prefix=prefix, intents=intents, help_command=None)

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
            "help", "invite_tracker", "leveling", "mafia", "mines",
            "moderation", "pvp", "roles", "shop", "stock",
            "stick", "marriage", "announcement", "tempvoice", "trade",
            "quests", "leaderboard", "casino", "greetings"
        ]

        for cog in cogs_to_load:
            try:
                await self.load_extension(f"cogs.{cog}")
                self.loaded_cogs.append(cog)
                logger.info("  ✅ %s.py loaded", cog)
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

    async def on_ready(self):
        logger.info("✅ %s is online!", self.user)
        logger.info("📊 Guilds: %d", len(self.guilds))
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name=f"{config.get('prefix', DEFAULT_PREFIX)}help | {BOT_NAME}"
            )
        )

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
