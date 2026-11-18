from __future__ import annotations

from pathlib import Path

import bot as bot_module


async def test_bot_loads_all_cogs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(bot_module.config, "DB_PATH", tmp_path / "bot.db")
    app = bot_module.AetherBot()
    await app.db.connect()
    try:
        for extension in bot_module.COGS:
            await app.load_extension(extension)
        assert set(app.cogs) == {"Health", "Economy", "Skills", "Admin"}
        names = {command.name for command in app.commands}
        assert {"ping", "balance", "skills", "upgrade", "activate"} <= names
    finally:
        await app.db.close()
