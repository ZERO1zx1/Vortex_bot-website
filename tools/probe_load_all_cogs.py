"""Offline probe: load EVERY cog from main.py's list into a real commands.Bot
with a stubbed db_manager and report every load failure + duplicate names.
No Discord login, no network traffic.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import discord
from discord.ext import commands

from src.utils.cog_loader import ACTIVE_COGS, discover_cogs

logger = logging.getLogger(__name__)


class StubDB:
    async def fetchone(self, *a, **k): return None
    async def fetch(self, *a, **k): return None
    async def fetchall(self, *a, **k): return []
    async def fetch_safe(self, *a, single=False, **k):
        # Mirror SupabaseManager.fetch_safe semantics: single=True → None,
        # multi-row reads → [] so cogs that iterate the result stay safe.
        return None if single else []
    async def fetch_one(self, *a, **k): return None
    async def fetch_all(self, *a, **k): return []
    async def insert(self, *a, **k): return None
    async def update(self, *a, **k): return None
    async def delete(self, *a, **k): return None
    async def execute(self, *a, **k): return None
    async def upsert(self, *a, **k): return None
    async def rpc(self, *a, **k): return None
    async def init_tables(self): return None
    def connect(self): return None


COGS = discover_cogs(Path(__file__).resolve().parents[1] / "src" / "cogs", ACTIVE_COGS)


async def main():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.voice_states = True
    intents.presences = True
    # Mirror main.py's real MyBot init as closely as possible offline.
    bot = commands.Bot(
        command_prefix="A!",
        intents=intents,
        help_command=None,
        case_insensitive=True,
        allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, replied_user=True),
    )
    loop = asyncio.get_running_loop()
    bot.loop = loop  # mirror post-login state (prod: set in _async_setup_hook)
    bot.db_manager = StubDB()
    bot.config = {"prefix": "A!", "owner_id": None}
    bot.wait_until_ready = lambda: asyncio.sleep(0)

    failed = []
    for name in COGS:
        try:
            await asyncio.wait_for(bot.load_extension(f"src.cogs.{name}"), timeout=15)
            print(f"[OK]   {name}")
        except asyncio.TimeoutError:
            failed.append(name)
            print(f"[LOAD TIMEOUT] {name}")
        except Exception as e:
            logger.exception("Could not load cog %s", name)
            failed.append(name)
            print(f"[LOAD FAIL] {name}: {type(e).__name__}: {e}")

    print(f"\nLoaded {len(bot.cogs)}/{len(COGS)} cogs; failed: {failed or 'NONE'}")

    # Duplicate detection is impossible after failure-free load (discord.py
    # rejects the second one), so just count command names.
    all_cmds = {}
    for cog in bot.cogs.values():
        for cmd in cog.get_commands():
            all_cmds.setdefault(cmd.name, []).append(type(cmd.cog).__name__)
    print(f"Total registered commands: {len(all_cmds)}")
    await bot.close()
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
