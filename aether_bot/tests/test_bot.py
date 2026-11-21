from __future__ import annotations

from pathlib import Path

from discord.ext import commands

import bot as bot_module

EXPECTED_COGS = {
    "System",
    "SystemEvents",
    "Admin",
    "Wallet",
    "Income",
    "Crime",
    "Profile",
    "Skills",
    "Shop",
    "Inventory",
    "Slots",
    "Blackjack",
    "Roulette",
    "Minefield",
    "Coinflip",
    "Crash",
    "Lottery",
    "Duel",
    "Adventure",
    "HuntFish",
    "Boss",
}


async def test_bot_loads_all_cogs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(bot_module.config, "DB_PATH", tmp_path / "bot.db")
    app = bot_module.AetherBot()
    await app.db.connect()
    try:
        for extension in bot_module.COGS:
            await app.load_extension(extension)
        assert set(app.cogs) == EXPECTED_COGS
        names = {command.name for command in app.commands}
        assert {
            "help",
            "ping",
            "balance",
            "skills",
            "upgrade",
            "activate",
            "slots",
            "blackjack",
            "duel",
        } <= names
        for command in app.commands:
            assert not isinstance(command, commands.HybridCommand)
        for name in (
            "admin_economy",
            "admin_jail",
            "admin_shop",
            "admin_skill",
            "admin_config",
        ):
            assert app.tree.get_command(name) is not None
    finally:
        await app.db.close()
