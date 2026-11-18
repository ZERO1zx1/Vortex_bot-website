from __future__ import annotations

import asyncio
from pathlib import Path

import aiosqlite
import pytest

import config
from core.database import Database


async def _count(db: Database, user_id: int | None = None) -> int:
    if user_id is None:
        return int(await db.fetchval("SELECT COUNT(*) FROM users"))
    return int(
        await db.fetchval("SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id,))
    )


async def test_schema_seed_and_idempotent_migration(
    db: Database, tmp_path: Path
) -> None:
    assert await db.fetchval("SELECT COUNT(*) FROM shop_items") == 6
    await db.close()

    again = Database(tmp_path / "aether-test.db", migrations_dir=config.MIGRATIONS_DIR)
    await again.connect()
    try:
        assert await again.fetchval("SELECT COUNT(*) FROM shop_items") == 6
    finally:
        await again.close()


async def test_read_does_not_see_uncommitted_write(db: Database) -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    async def writer() -> None:
        try:
            async with db.transaction():
                await db.execute("INSERT INTO users (user_id, wallet) VALUES (1, 500)")
                started.set()
                await release.wait()
                raise RuntimeError("rollback")
        except RuntimeError:
            pass

    task = asyncio.create_task(writer())
    await asyncio.wait_for(started.wait(), timeout=1.0)
    assert await _count(db, 1) == 0
    release.set()
    await asyncio.wait_for(task, timeout=1.0)
    assert await _count(db, 1) == 0


async def test_standalone_write_waits_for_foreign_transaction(db: Database) -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    written = asyncio.Event()

    async def holder() -> None:
        try:
            async with db.transaction():
                await db.execute("INSERT INTO users (user_id, wallet) VALUES (1, 500)")
                started.set()
                await release.wait()
                raise RuntimeError("rollback")
        except RuntimeError:
            pass

    async def writer() -> None:
        await started.wait()
        await db.execute("INSERT INTO users (user_id, wallet) VALUES (2, 500)")
        written.set()

    holder_task = asyncio.create_task(holder())
    writer_task = asyncio.create_task(writer())
    await asyncio.wait_for(started.wait(), timeout=1.0)
    await asyncio.sleep(0.05)
    assert not written.is_set()
    release.set()
    await asyncio.wait_for(asyncio.gather(holder_task, writer_task), timeout=1.0)
    assert written.is_set()
    assert await _count(db, 1) == 0
    assert await _count(db, 2) == 1


async def test_task_spawned_inside_transaction_cannot_write(db: Database) -> None:
    errors: list[RuntimeError] = []

    async def holder() -> None:
        async with db.transaction():
            await db.execute("INSERT INTO users (user_id, wallet) VALUES (1, 500)")

            async def child() -> None:
                try:
                    await db.execute(
                        "INSERT INTO users (user_id, wallet) VALUES (2, 500)"
                    )
                except RuntimeError as exc:
                    errors.append(exc)

            await asyncio.create_task(child())

    await holder()
    assert errors
    assert await _count(db) == 1
    assert await _count(db, 1) == 1


async def test_commit_failure_rolls_back_and_recovers(
    db: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    conn = db._require()
    real_commit = conn.commit
    calls = 0

    async def flaky_commit() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("simulated commit failure")
        await real_commit()

    monkeypatch.setattr(conn, "commit", flaky_commit)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        async with db.transaction():
            await db.execute("INSERT INTO users (user_id, wallet) VALUES (1, 500)")

    # Холболт түгжигдээгүй эсэхийг шалгана.
    async with db.transaction():
        await db.execute("INSERT INTO users (user_id, wallet) VALUES (2, 500)")

    assert await _count(db, 1) == 0
    assert await _count(db, 2) == 1


async def test_nested_transaction_rolls_back_with_outer(db: Database) -> None:
    with pytest.raises(RuntimeError):
        async with db.transaction():
            await db.execute("INSERT INTO users (user_id, wallet) VALUES (1, 500)")
            async with db.transaction():
                await db.execute("INSERT INTO users (user_id, wallet) VALUES (2, 500)")
            raise RuntimeError("outer rollback")

    assert await _count(db) == 0


async def test_two_databases_do_not_share_transaction_state(
    db: Database, tmp_path: Path
) -> None:
    other = Database(tmp_path / "other.db", migrations_dir=config.MIGRATIONS_DIR)
    await other.connect()
    try:
        with pytest.raises(RuntimeError, match="outer rollback"):
            async with db.transaction():
                await db.execute("INSERT INTO users (user_id, wallet) VALUES (1, 500)")
                # Хоёр дахь Database ижил task-д бичихдээ эхний DB-ийн
                # транзакцад нэгдэх ёсгүй.
                await other.execute(
                    "INSERT INTO users (user_id, wallet) VALUES (2, 500)"
                )
                raise RuntimeError("outer rollback")

        assert await _count(db, 1) == 0
        assert await _count(other, 2) == 1
    finally:
        await other.close()


async def test_in_memory_database_works() -> None:
    database = Database(":memory:", migrations_dir=config.MIGRATIONS_DIR)
    await database.connect()
    try:
        await database.execute("INSERT INTO users (user_id, wallet) VALUES (1, 500)")
        assert await _count(database, 1) == 1
    finally:
        await database.close()


async def test_missing_migrations_dir_fails_fast(tmp_path: Path) -> None:
    database = Database(tmp_path / "missing.db", migrations_dir=tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        await database.connect()
    await database.close()


async def test_migrations_are_recorded_once(db: Database) -> None:
    rows = await db.fetchall(
        "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
    )
    assert [row["version"] for row in rows] == [1, 2, 3]
    assert all(row["checksum"] and len(row["checksum"]) == 64 for row in rows)


async def test_legacy_schema_migrations_row_is_backfilled(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    script = (config.MIGRATIONS_DIR / "001_baseline.sql").read_text(encoding="utf-8")
    async with aiosqlite.connect(path, isolation_level=None) as conn:
        await conn.executescript(script)
        await conn.execute(
            "CREATE TABLE schema_migrations ("
            "version INTEGER PRIMARY KEY, "
            "applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
        )
        await conn.execute("INSERT INTO schema_migrations (version) VALUES (1)")
        await conn.commit()

    database = Database(path, migrations_dir=config.MIGRATIONS_DIR)
    await database.connect()
    try:
        rows = await database.fetchall(
            "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
        )
        assert [row["version"] for row in rows] == [1, 2, 3]
        assert rows[0]["name"] == "baseline"
        assert rows[0]["checksum"] is not None
        assert len(rows[0]["checksum"]) == 64
    finally:
        await database.close()


async def test_seed_changes_do_not_resurrect_on_reconnect(
    db: Database, tmp_path: Path
) -> None:
    await db.execute(
        "UPDATE shop_items SET price = 1234 WHERE item_id = 'xp_potion_2x'"
    )
    await db.close()

    again = Database(tmp_path / "aether-test.db", migrations_dir=config.MIGRATIONS_DIR)
    await again.connect()
    try:
        price = await again.fetchval(
            "SELECT price FROM shop_items WHERE item_id = 'xp_potion_2x'"
        )
        assert price == 1234
    finally:
        await again.close()


async def test_changed_migration_checksum_is_rejected(
    db: Database, tmp_path: Path
) -> None:
    import shutil

    await db.close()
    copy = tmp_path / "migrations"
    shutil.copytree(config.MIGRATIONS_DIR, copy)
    database = Database(tmp_path / "checksum.db", migrations_dir=copy)
    await database.connect()
    await database.close()

    target = copy / "001_baseline.sql"
    target.write_text(target.read_text() + "\n-- edited\n", encoding="utf-8")

    broken = Database(tmp_path / "checksum.db", migrations_dir=copy)
    with pytest.raises(RuntimeError, match="өөрчлөгдсөн"):
        await broken.connect()
    await broken.close()


async def test_hardening_constraints_and_append_only(db: Database) -> None:
    import sqlite3

    await db.execute("INSERT INTO users (user_id, wallet) VALUES (99, 500)")
    await db.execute(
        "INSERT INTO shop_items "
        "(item_id, name, category, price, description, effect_type) "
        "VALUES ('pickaxe', 'Pickaxe', 'tool', 100, 'test', 'tool')"
    )
    await db.execute(
        "INSERT INTO casino_logs (user_id, game, bet, outcome) "
        "VALUES (99, 'coinflip', 10, 'win')"
    )
    await db.execute(
        "INSERT INTO game_logs (kind, user_id, outcome) VALUES ('boss', 99, 'win')"
    )
    await db.execute("INSERT INTO guild_settings (guild_id, prefix) VALUES (1, 'a!')")
    await db.execute(
        "INSERT INTO transactions (user_id, amount, source) VALUES (99, 10, 'test')"
    )

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        await db.execute("UPDATE transactions SET amount = 11 WHERE user_id = 99")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        await db.execute("DELETE FROM transactions WHERE user_id = 99")
    with pytest.raises(sqlite3.IntegrityError):
        await db.execute(
            "INSERT INTO shop_items "
            "(item_id, name, category, price, description, effect_type) "
            "VALUES ('bad', 'Bad', 'weapon', 100, 'test', 'tool')"
        )
