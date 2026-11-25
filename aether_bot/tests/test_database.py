from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest

from core.database import Database


class FakeTransaction:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> None:
        self.connection.events.append("begin")

    async def __aexit__(self, exc_type: type[BaseException] | None, *_: object) -> None:
        self.connection.events.append("rollback" if exc_type else "commit")


class FakeConnection:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.rows: list[dict[str, Any]] = []
        self.value: Any = None

    def transaction(self) -> FakeTransaction:
        return FakeTransaction(self)

    async def execute(self, sql: str, *params: Any) -> str:
        self.events.append(f"execute:{sql}:{params}")
        return "UPDATE 1"

    async def executemany(self, sql: str, params: Any) -> None:
        self.events.append(f"executemany:{sql}:{list(params)}")

    async def fetchrow(self, sql: str, *params: Any) -> dict[str, Any] | None:
        self.events.append(f"fetchrow:{sql}:{params}")
        return self.rows[0] if self.rows else None

    async def fetch(self, sql: str, *params: Any) -> list[dict[str, Any]]:
        self.events.append(f"fetch:{sql}:{params}")
        return self.rows

    async def fetchval(self, sql: str, *params: Any) -> Any:
        self.events.append(f"fetchval:{sql}:{params}")
        return self.value


class FakePool:
    def __init__(self) -> None:
        self.connection = FakeConnection()
        self.closed = False

    @asynccontextmanager
    async def acquire(self):
        yield self.connection

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def pool() -> FakePool:
    return FakePool()


@pytest.fixture
async def database(
    monkeypatch: pytest.MonkeyPatch, pool: FakePool
) -> AsyncIterator[Database]:
    async def create_pool(**kwargs: Any) -> FakePool:
        pool.connection.events.append(f"pool:{kwargs}")
        return pool

    monkeypatch.setattr("core.database.asyncpg.create_pool", create_pool)
    db = Database("postgresql://postgres:secret@example.test/postgres")
    await db.connect()
    try:
        yield db
    finally:
        await db.close()


async def test_connect_requires_tls_and_disables_statement_cache(
    database: Database, pool: FakePool
) -> None:
    event = pool.connection.events[0]
    assert "'ssl': 'require'" in event
    assert "'statement_cache_size': 0" in event
    assert database.connected


async def test_close_closes_pool(database: Database, pool: FakePool) -> None:
    await database.close()
    assert pool.closed
    assert not database.connected


async def test_execute_wraps_write_in_transaction(
    database: Database, pool: FakePool
) -> None:
    affected = await database.execute("UPDATE users SET wallet = $1", (500,))
    assert affected == 1
    assert pool.connection.events[-3:] == [
        "begin",
        "execute:UPDATE users SET wallet = $1:(500,)",
        "commit",
    ]


async def test_explicit_transaction_rolls_back_all_writes(
    database: Database, pool: FakePool
) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        async with database.transaction():
            await database.execute("UPDATE one SET value = $1", (1,))
            raise RuntimeError("boom")
    assert pool.connection.events[-3:] == [
        "begin",
        "execute:UPDATE one SET value = $1:(1,)",
        "rollback",
    ]


async def test_nested_transaction_uses_one_database_transaction(
    database: Database, pool: FakePool
) -> None:
    async with database.transaction(), database.transaction():
        await database.execute("UPDATE one SET value = $1", (1,))
    assert pool.connection.events.count("begin") == 1
    assert pool.connection.events.count("commit") == 1


async def test_transaction_context_cannot_write_from_child_task(
    database: Database,
) -> None:
    async with database.transaction():
        result = await asyncio.gather(
            asyncio.create_task(database.execute("UPDATE one SET value = 1")),
            return_exceptions=True,
        )
    assert isinstance(result[0], RuntimeError)
    assert "өөр task" in str(result[0])


async def test_fetch_helpers_return_mapping_rows(
    database: Database, pool: FakePool
) -> None:
    pool.connection.rows = [{"user_id": 1}, {"user_id": 2}]
    assert await database.fetchone("SELECT * FROM users") == {"user_id": 1}
    assert await database.fetchall("SELECT * FROM users") == [
        {"user_id": 1},
        {"user_id": 2},
    ]


async def test_changed_applied_migration_is_rejected(
    monkeypatch: pytest.MonkeyPatch, pool: FakePool, tmp_path: Path
) -> None:
    migration = tmp_path / "001_baseline.sql"
    migration.write_text("SELECT 1;", encoding="utf-8")
    pool.connection.rows = [{"version": 1, "name": "baseline", "checksum": "wrong"}]

    async def create_pool(**_: Any) -> FakePool:
        return pool

    monkeypatch.setattr("core.database.asyncpg.create_pool", create_pool)
    db = Database(
        "postgresql://postgres:secret@example.test/postgres",
        migrations_dir=tmp_path,
    )
    with pytest.raises(RuntimeError, match="өөрчлөгдсөн"):
        await db.connect()
    assert any("pg_advisory_xact_lock" in event for event in pool.connection.events)
    assert any("ENABLE ROW LEVEL SECURITY" in event for event in pool.connection.events)


async def test_applied_migration_missing_from_disk_is_rejected(
    monkeypatch: pytest.MonkeyPatch, pool: FakePool, tmp_path: Path
) -> None:
    (tmp_path / "002_second.sql").write_text("SELECT 2;", encoding="utf-8")
    pool.connection.rows = [{"version": 1, "name": "baseline", "checksum": "unused"}]

    async def create_pool(**_: Any) -> FakePool:
        return pool

    monkeypatch.setattr("core.database.asyncpg.create_pool", create_pool)
    db = Database(
        "postgresql://postgres:secret@example.test/postgres",
        migrations_dir=tmp_path,
    )
    with pytest.raises(RuntimeError, match="файл нь байхгүй"):
        await db.connect()
