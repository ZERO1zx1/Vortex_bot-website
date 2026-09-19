"""Diff the help catalog (COMMAND_INFO in src/cogs/help.py) against the commands
actually registered after loading all cogs offline.

Reports:
  - Documented but NOT registered (dead help entries)
  - Registered but not documented (undocumented commands)
"""
import asyncio
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ast
import discord
from discord.ext import commands

from probe_load_all_cogs import StubDB, COGS


def extract_command_info_keys():
    """Parse COMMAND_INFO dict literal from src/cogs/help.py via AST."""
    src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "cogs", "help.py")
    tree = ast.parse(open(src_path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "COMMAND_INFO":
                    d = ast.literal_eval(node.value)
                    return d
    return {}


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
            failures.append((name, f"{type(e).__name__}: {e}"))
    if failures:
        print("LOAD FAILURES (unexpected):")
        for n, e in failures:
            print(" ", n, e)

    registered = set(bot.all_commands.keys())  # top-level names + aliases
    slash = set()

    def walk(cmd, prefix=""):
        full = prefix + cmd.name
        slash.add(full)
        children = getattr(cmd, "_children", {}) or {}
        for sub in children.values():
            walk(sub, full + " ")

    for cmd in bot.tree.get_commands():
        walk(cmd)

    # Context menus / standalone commands registered directly.
    slash.update(c.name for c in bot.tree._context_menus.values())

    # Prefix subcommands (e.g. "stock add", "quest refresh") via walk_commands.
    for cmd in bot.walk_commands():
        qn = cmd.qualified_name
        registered.add(qn)
        # alias variants: parent aliases + leaf alias
        leaf_alias = getattr(cmd, "aliases", [])
        for a in leaf_alias:
            registered.add(qn.rsplit(" ", 1)[0] + " " + a if " " in qn else a)
        parent = getattr(cmd, "parent", None)
        while parent is not None:
            for pa in getattr(parent, "aliases", []):
                registered.add(qn.replace(parent.name, pa, 1))
            parent = getattr(parent, "parent", None)

    doc = extract_command_info_keys()
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

    if missing:
        sys.exit(1)

asyncio.run(main())