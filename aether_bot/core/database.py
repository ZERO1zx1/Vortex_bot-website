"""Supabase PostgreSQL pool, migrations, and atomic transactions."""

from __future__ import annotations

import asyncio
import hashlib
import re
from collections.abc import AsyncIterator, Iterable, Mapping, Sequence
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

import asyncpg  # type: ignore[import-untyped]

Params = Sequence[Any]
Row = Mapping[str, Any]
_MIGRATION_RE = re.compile(r"^(\d{3,})_([A-Za-z0-9_]+)\.sql$")
_LEAKED_TX_MESSAGE = (
    "DB транзакц өөр task руу тархсан байна — transaction() дотор "
    "create_task хийхгүй байх."
)


class DatabaseTimestamp(str):
    """Explicit marker for values bound to TIMESTAMPTZ columns."""


def _postgres_sql(sql: str) -> str:
    """Repository `?` placeholders → asyncpg `$n`, string literals untouched."""
    result: list[str] = []
    quoted = False
    index = 0
    position = 0
    while position < len(sql):
        char = sql[position]
        if char == "'":
            result.append(char)
            if quoted and position + 1 < len(sql) and sql[position + 1] == "'":
                result.append("'")
                position += 2
                continue
            quoted = not quoted
        elif char == "?" and not quoted:
            index += 1
            result.append(f"${index}")
        else:
            result.append(char)
        position += 1
    return "".join(result)


def _postgres_params(params: Params) -> tuple[Any, ...]:
    """Convert only explicitly marked timestamps to native datetime values."""
    converted: list[Any] = []
    for value in params:
        if isinstance(value, DatabaseTimestamp):
            moment = datetime.fromisoformat(str(value))
            converted.append(
                moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment
            )
        else:
            converted.append(value)
    return tuple(converted)


@dataclass(slots=True)
class _TxState:
    db: Database
    connection: asyncpg.Connection
    owner: asyncio.Task[Any] | None
    active: bool = True


_tx_state: ContextVar[_TxState | None] = ContextVar("aether_tx_state", default=None)


class Database:
    def __init__(
        self,
        database_url: str,
        migrations_dir: str | Path | None = None,
    ) -> None:
        self.database_url = database_url
        self.migrations_dir = Path(migrations_dir) if migrations_dir else None
        self._pool: asyncpg.Pool | None = None
        self._connect_lock = asyncio.Lock()
        self._migration_lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._pool is not None

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database.connect() дуудагдаагүй байна.")
        return self._pool

    async def connect(self) -> Self:
        async with self._connect_lock:
            if self._pool is not None:
                return self
            self._pool = await asyncpg.create_pool(
                dsn=self.database_url,
                min_size=1,
                max_size=10,
                ssl="require",
                statement_cache_size=0,
            )
            try:
                await self.migrate()
            except BaseException:
                await self._pool.close()
                self._pool = None
                raise
        return self

    async def close(self) -> None:
        if self.in_transaction():
            raise RuntimeError("transaction() дотор Database.close() дуудахгүй.")
        pool, self._pool = self._pool, None
        if pool is not None:
            await pool.close()

    async def __aenter__(self) -> Self:
        return await self.connect()

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    def _current_tx(self) -> _TxState | None:
        state = _tx_state.get()
        if state is None or not state.active or state.db is not self:
            return None
        return state

    def _owned_tx(self) -> _TxState | None:
        state = self._current_tx()
        if state is not None and state.owner is not asyncio.current_task():
            raise RuntimeError(_LEAKED_TX_MESSAGE)
        return state

    def in_transaction(self) -> bool:
        state = self._current_tx()
        try:
            return state is not None and state.owner is asyncio.current_task()
        except RuntimeError:
            return False

    @asynccontextmanager
    async def transaction(self, *, immediate: bool = True) -> AsyncIterator[Any]:
        del immediate  # Backward-compatible service API; PostgreSQL handles locks.
        state = self._owned_tx()
        if state is not None:
            yield state.connection
            return

        async with (
            self._require_pool().acquire() as connection,
            connection.transaction(),
        ):
            state = _TxState(self, connection, asyncio.current_task())
            token = _tx_state.set(state)
            try:
                yield connection
            finally:
                state.active = False
                _tx_state.reset(token)

    @asynccontextmanager
    async def _read_connection(self) -> AsyncIterator[Any]:
        state = self._current_tx()
        if state is not None and state.owner is asyncio.current_task():
            yield state.connection
            return
        async with self._require_pool().acquire() as connection:
            yield connection

    @staticmethod
    def _affected(status: str) -> int:
        try:
            return int(status.rsplit(" ", 1)[-1])
        except ValueError:
            return 0

    async def execute(self, sql: str, params: Params = ()) -> int:
        bound = _postgres_params(params)
        state = self._owned_tx()
        if state is not None:
            return self._affected(
                await state.connection.execute(_postgres_sql(sql), *bound)
            )
        async with self.transaction() as connection:
            return self._affected(await connection.execute(_postgres_sql(sql), *bound))

    async def insert(self, sql: str, params: Params = ()) -> int:
        value = await self.fetchval_write(sql, params)
        return int(value or 0)

    async def executemany(self, sql: str, seq: Iterable[Params]) -> int:
        rows = [_postgres_params(params) for params in seq]
        state = self._owned_tx()
        if state is not None:
            await state.connection.executemany(_postgres_sql(sql), rows)
        else:
            async with self.transaction() as connection:
                await connection.executemany(_postgres_sql(sql), rows)
        return len(rows)

    async def fetchone(self, sql: str, params: Params = ()) -> Row | None:
        async with self._read_connection() as connection:
            return await connection.fetchrow(
                _postgres_sql(sql), *_postgres_params(params)
            )

    async def fetchall(self, sql: str, params: Params = ()) -> list[Row]:
        async with self._read_connection() as connection:
            return list(
                await connection.fetch(_postgres_sql(sql), *_postgres_params(params))
            )

    async def fetchval(self, sql: str, params: Params = (), default: Any = None) -> Any:
        async with self._read_connection() as connection:
            value = await connection.fetchval(
                _postgres_sql(sql), *_postgres_params(params)
            )
        return default if value is None else value

    async def fetchval_write(
        self, sql: str, params: Params = (), default: Any = None
    ) -> Any:
        state = self._owned_tx()
        bound = _postgres_params(params)
        if state is not None:
            value = await state.connection.fetchval(_postgres_sql(sql), *bound)
        else:
            async with self.transaction() as connection:
                value = await connection.fetchval(_postgres_sql(sql), *bound)
        return default if value is None else value

    async def advisory_xact_lock(self, key: int) -> None:
        """Serialize one logical resource across every bot process."""
        state = self._owned_tx()
        if state is None:
            raise RuntimeError("advisory_xact_lock() нь transaction() дотор ажиллана.")
        lock_key = int.from_bytes(
            hashlib.blake2b(f"aether:user:{key}".encode(), digest_size=8).digest(),
            "big",
            signed=True,
        )
        await state.connection.fetchval("SELECT pg_advisory_xact_lock($1)", lock_key)

    async def migrate(self) -> None:
        if self.migrations_dir is None:
            return
        if not self.migrations_dir.is_dir():
            raise FileNotFoundError(
                f"migrations хавтас олдсонгүй: {self.migrations_dir}"
            )
        files = sorted(
            path
            for path in self.migrations_dir.iterdir()
            if path.is_file() and _MIGRATION_RE.match(path.name)
        )
        if not files:
            raise RuntimeError(f"migration файл олдсонгүй: {self.migrations_dir}")

        async with self._migration_lock, self.transaction() as connection:
            await connection.fetchval(
                "SELECT pg_advisory_xact_lock($1)", 0x4145544845524442
            )
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            await connection.execute(
                "ALTER TABLE schema_migrations ENABLE ROW LEVEL SECURITY"
            )
            applied = {
                int(row["version"]): (row["name"], row["checksum"])
                for row in await connection.fetch(
                    "SELECT version, name, checksum FROM schema_migrations"
                )
            }
            available_versions = {
                int(match.group(1))
                for path in files
                if (match := _MIGRATION_RE.match(path.name)) is not None
            }
            missing = set(applied) - available_versions
            if missing:
                raise RuntimeError(
                    "schema_migrations-д бүртгэгдсэн боловч файл нь байхгүй "
                    f"migration: {sorted(missing)}"
                )
            disk_versions: set[int] = set()
            for path in files:
                match = _MIGRATION_RE.match(path.name)
                assert match is not None
                version, name = int(match.group(1)), match.group(2)
                if version in disk_versions:
                    raise RuntimeError(f"давхардсан migration version: {version}")
                disk_versions.add(version)
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if version in applied:
                    if applied[version][1] != digest:
                        raise RuntimeError(f"Migration {path.name} өөрчлөгдсөн байна.")
                    continue
                await connection.execute(path.read_text(encoding="utf-8"))
                await connection.execute(
                    "INSERT INTO schema_migrations (version, name, checksum) "
                    "VALUES ($1, $2, $3)",
                    version,
                    name,
                    digest,
                )
