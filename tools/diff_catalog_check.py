"""Diff the help catalog (COMMAND_INFO in src/cogs/help.py) against the commands
actually registered after loading all cogs offline.

Reports:
  - Documented but NOT registered (dead help entries)
  - Registered but not documented (undocumented commands)
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import discord
from discord.ext import commands
from probe_load_all_cogs import COGS, StubDB

logger = logging.getLogger(__name__)


async def main():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.voice_states = True
    intents.presences = True
    bot = commands.Bot(command_prefix="A!", intents=intents, help_command=None, case_insensitive=True)
    loop = asyncio.get_running_loop()
    bot.loop = loop
    bot.db_manager = StubDB()
    bot.config = {"prefix": "A!", "owner_id": None}
    bot.wait_until_ready = lambda: asyncio.sleep(0)

    failures = []
    for name in COGS:
        try:
            await bot.load_extension(f"src.cogs.{name}")
        except Exception as e:
            logger.exception("Could not load cog %s for catalog comparison", name)
            failures.append((name, f"{type(e).__name__}: {e}"))
    if failures:
        print("LOAD FAILURES (unexpected):")
        for n, e in failures:
            print(" ", n, e)

    # Canonical names only. Aliases intentionally share their command's help
    # entry and must not be reported as undocumented commands.
    registered = {cmd.qualified_name for cmd in bot.walk_commands()}
    slash = set()

    def walk(cmd, prefix=""):
        full = prefix + cmd.name
        children = getattr(cmd, "_children", {}) or {}
        if not children:
            slash.add(full)
        for sub in children.values():
            walk(sub, full + " ")

    for cmd in bot.tree.get_commands():
        walk(cmd)

    # Context menus / standalone commands registered directly.
    slash.update(c.name for c in bot.tree._context_menus.values())

    # Help.cog_load prunes documentation for cogs excluded by ACTIVE_COGS.
    # Compare against that runtime catalog, not the unpruned source literal.
    from src.cogs.help import COMMAND_INFO
    doc = dict(COMMAND_INFO)
    documented = set(doc.keys())

    print(f"\nRegistered: {len(registered)} prefix names/aliases + {len(slash)} slash paths")
    print(f"Documented (COMMAND_INFO): {len(documented)} entries")

    def resolve_key(k):
        if k in registered or k in slash:
            return True
        if " " in k:
            return False, "slash"
        return False, "prefix"

    missing = []
    for k in documented:
        if k not in registered and k not in slash:
            missing.append(k)
            d = doc[k]
            print(f"[MISSING] '{k}' -- usage: {d.get('usage')} | {d.get('description_mn')}")

    extra = (registered | slash) - documented
    print(f"\nDocumented-but-unregistered: {len(missing)}")
    print(f"Registered-but-undocumented: {len(extra)}")
    if extra:
        print("  (first 40):", sorted(extra)[:40])

    if missing or failures:
        await bot.close()
        sys.exit(1)
    await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
