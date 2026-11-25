from __future__ import annotations

from pathlib import Path
from typing import Any

from discord.ext import commands

import bot as bot_module
from tests.fakes.database import SqliteTestDatabase

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


def test_bot_constructs_database_from_supabase_url(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class CapturingDatabase:
        def __init__(self, database_url: str, *, migrations_dir: Any) -> None:
            captured["url"] = database_url
            captured["migrations_dir"] = migrations_dir

    monkeypatch.setattr(bot_module.config, "DATABASE_URL", "postgresql://example")
    monkeypatch.setattr(bot_module, "Database", CapturingDatabase)
    app = bot_module.AetherBot()
    assert captured == {
        "url": "postgresql://example",
        "migrations_dir": bot_module.config.MIGRATIONS_DIR,
    }
    assert app.db is not None


async def test_bot_loads_all_cogs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(bot_module.config, "DATABASE_URL", "postgresql://test")
    monkeypatch.setattr(
        bot_module,
        "Database",
        lambda *_args, **_kwargs: SqliteTestDatabase(tmp_path / "bot.db"),
    )
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
