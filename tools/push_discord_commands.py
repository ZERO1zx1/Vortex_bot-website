#!/usr/bin/env python3
"""Load Aether's cogs and publish the current slash-command registry."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import discord
from discord.ext import commands
from dotenv import load_dotenv

from src.utils.cog_loader import ACTIVE_COGS, discover_cogs
from tools.probe_load_all_cogs import StubDB


async def publish(guild_id: int | None) -> None:
    load_dotenv(ROOT / ".env")
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise SystemExit("ERROR: DISCORD_TOKEN not found in .env")

    bot = commands.Bot(command_prefix="A!", intents=discord.Intents.none(), help_command=None)
    bot.db_manager = StubDB()
    bot.config = {"prefix": "A!", "owner_id": None}

    try:
        await bot.login(token)
        cog_dir = ROOT / "src" / "cogs"
        for name in discover_cogs(cog_dir, ACTIVE_COGS):
            await bot.load_extension(f"src.cogs.{name}")

        synced = await bot.tree.sync()
        print(f"Global registry synced: {len(synced)} root commands")

        if guild_id is not None:
            guild = discord.Object(id=guild_id)
            bot.tree.copy_global_to(guild=guild)
            guild_synced = await bot.tree.sync(guild=guild)
            print(f"Guild {guild_id} synced: {len(guild_synced)} root commands")
    finally:
        await bot.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish Aether slash commands to Discord.")
    parser.add_argument("--guild", type=int, help="Also copy and sync commands to this guild.")
    args = parser.parse_args()
    asyncio.run(publish(args.guild))


if __name__ == "__main__":
    main()
