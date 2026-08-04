import discord
from discord.ext import commands
import os
import sys
import asyncio
from dotenv import load_dotenv

# Local imports
from config_manager import load_config
from database.manager import DatabaseManager
from database.schema import TABLES, ALTER_QUERIES, INDEXES
from utils.constants import PREFIXES

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ DISCORD_TOKEN not found! Check your .env file.")
    sys.exit(1)

config = load_config()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True

        super().__init__(command_prefix=PREFIXES, intents=intents, help_command=None)
        
        self.db_manager = DatabaseManager()
        self.owner_ids = set()
        owner = config.get("owner_id")
        if owner:
            self.owner_ids.add(owner)
        co_owners = config.get("co_owner_ids", [])
        for co in co_owners:
            self.owner_ids.add(co)

        self.config = config

    async def setup_hook(self):
        # Connect to Database
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.db = await self.db_manager.connect()
                print(f"✅ MySQL connected (Attempt {attempt+1})")
                break
            except Exception as e:
                print(f"Waiting for MySQL... ({attempt+1}/{max_retries}) - {e}")
                if attempt == max_retries - 1:
                    raise RuntimeError("Could not connect to MySQL") from e
                await asyncio.sleep(5)

        # Initialize Tables
        await self.db_manager.init_tables(TABLES)
        for query in ALTER_QUERIES + INDEXES:
            try:
                await self.db_manager.execute(query)
            except:
                pass

        # Load Cogs
        print("\n📂 Loading Cogs...")
        cogs_to_load = [
            "admin", "avatar_check", "cafe", "carts", "confessions",
            "counting", "economy", "fun", "games", "giveaway",
            "help", "invite_tracker", "leveling", "mafia", "mines",
            "moderation", "pvp", "roles", "shop", "stock",
            "stick", "marriage", "announcement", "tempvoice", "trade",
            "quests", "leaderboard"
        ]

        for cog in cogs_to_load:
            try:
                await self.load_extension(f"cogs.{cog}")
                print(f"  ✅ {cog}.py loaded")
            except Exception as e:
                print(f"  ❌ Error loading {cog}.py: {e}")

        # Sync Slash Commands
        try:
            synced = await self.tree.sync()
            print(f"✅ {len(synced)} slash commands synced.")
        except Exception as e:
            print(f"⚠️ Slash command sync error: {e}")

    async def on_ready(self):
        print(f'✅ {self.user} is online!')
        print(f'📊 Guilds: {len(self.guilds)}')
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name=f"{PREFIXES[0]}help | Gurten|LGC"
            )
        )

    async def close(self):
        await self.db_manager.close()
        await super().close()

if __name__ == "__main__":
    # Ensure utils/constants.py has PREFIXES
    # Let's double check constants.py
    bot = MyBot()
    try:
        bot.run(TOKEN, reconnect=True)
    except Exception as e:
        print(f"❌ Error: {e}")
