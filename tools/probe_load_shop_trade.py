"""Offline probe: load cogs.shop then cogs.trade into a real commands.Bot
with a stubbed db_manager and report every load error + registered names.
No Discord login, no network traffic.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import discord
from discord.ext import commands


class StubDB:
    async def fetchone(self, *a, **k): return None
    async def fetch(self, *a, **k): return None
    async def fetchall(self, *a, **k): return []
    async def fetch_one(self, *a, **k): return None
    async def fetch_all(self, *a, **k): return []
    async def insert(self, *a, **k): return None
    async def update(self, *a, **k): return None
    async def delete(self, *a, **k): return None
    async def execute(self, *a, **k): return None
    async def upsert(self, *a, **k): return None
    async def init_tables(self): return None
    def connect(self): return None


async def main():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.voice_states = True
    intents.presences = True
    bot = commands.Bot(command_prefix="A!", intents=intents)
    bot.db_manager = StubDB()
    bot.config = {}

    for ext in ("src.cogs.shop", "src.cogs.trade"):
        try:
            await asyncio.wait_for(bot.load_extension(ext), timeout=15)
            print(f"[OK] loaded {ext}")
        except Exception as e:
            print(f"[LOAD FAIL] {ext}: {type(e).__name__}: {e}")

    names = sorted(bot.all_commands.keys())
    print(f"cogs: {list(bot.cogs.keys())}")
    print("command names:", names)
    t = bot.all_commands.get("trade")
    if t is not None:
        print("owner of 'trade':", t.qualified_name, "| module:", t.module,
              "| cog:", type(t.cog).__name__ if t.cog else None,
              "| hybrid:", isinstance(t, commands.HybridCommand))
    await bot.close()


asyncio.run(main())