from __future__ import annotations

from pathlib import Path

import pytest

from tests.fakes.database import SqliteTestDatabase


async def test_test_database_supports_repository_contract(tmp_path: Path) -> None:
    async with SqliteTestDatabase(tmp_path / "contract.db") as db:
        assert await db.fetchval("SELECT COUNT(*) FROM shop_items") == 6
        await db.execute("INSERT INTO users (user_id) VALUES (?)", (1,))
        assert (
            await db.fetchval("SELECT wallet FROM users WHERE user_id = ?", (1,)) == 500
        )


async def test_test_database_rolls_back_explicit_transaction(tmp_path: Path) -> None:
    async with SqliteTestDatabase(tmp_path / "rollback.db") as db:
        with pytest.raises(RuntimeError):
            async with db.transaction():
                await db.execute("INSERT INTO users (user_id) VALUES (?)", (1,))
                raise RuntimeError("rollback")
        assert await db.fetchval("SELECT COUNT(*) FROM users") == 0
