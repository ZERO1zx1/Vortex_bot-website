"""SQLite (aiosqlite) холболт, WAL тохиргоо, migration runner, atomic transaction.

Гол санаа:
- Бичих үйлдэл бүр нэг л бичих холболт (`_conn`) дээр, `_write_lock`-оор
  цуварсан байдлаар гүйцэтгэгдэнэ. Транзакц `BEGIN IMMEDIATE`-ээр эхэлнэ.
- Уншилт нь тусдаа `_read_conn` холболтоор явна. WAL горимд уншилт нь
  commit хараахан болоогүй өгөгдлийг харахгүй, мөн нэг task-ийн `ROLLBACK`
  нь өөр task-ийн бичилтийг буцаахгүй.
- Транзакц идэвхтэй үед `ContextVar`-д `_TxState` хадгалагдана. Төлөв нь
  тухайн `Database` instance-д хамаарах тул нэг task дотор хоёр сан
  ашигласан ч транзакцууд холилдохгүй. Зөвхөн транзакцыг эзэмшсэн task ижил
  холболтыг ашиглана; `create_task`-аар тархсан context-ийг илрүүлж, бичих
  үед тодорхой алдаа шиднэ.
- `:memory:` үед тусдаа холболт ижил санг харахгүй тул уншилт, бичилт нэг
  холболтыг хуваалцана. Энэ горим зөвхөн ганц task-ийн тестэд тохиромжтой.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Sequence
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self, TypeVar

import aiosqlite

log = logging.getLogger(__name__)

Params = Sequence[Any] | dict[str, Any]
T = TypeVar("T")

_MIGRATION_RE = re.compile(r"^(\d{3,})_([A-Za-z0-9_]+)\.sql$")

_LEAKED_TX_MESSAGE = (
    "DB транзакц өөр task руу тархсан байна — transaction() дотор "
    "create_task хийхгүй байх."
)


@dataclass(slots=True)
class _TxState:
    db: Database
    conn: aiosqlite.Connection
    owner: asyncio.Task[Any] | None
    active: bool = True


_tx_state: ContextVar[_TxState | None] = ContextVar("aether_tx_state", default=None)


class Database:
    def __init__(
        self,
        path: str | Path,
        migrations_dir: str | Path | None = None,
    ) -> None:
        self.path = str(path)
        self.migrations_dir = Path(migrations_dir) if migrations_dir else None
        self._conn: aiosqlite.Connection | None = None
        self._read_conn: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()
        self._connect_lock = asyncio.Lock()

    # ── Lifecycle ───────────────────────────────────────────────────────
    async def connect(self) -> Self:
        async with self._connect_lock:
            if self._conn is not None:
                return self

            if self.path != ":memory:":
                Path(self.path).expanduser().parent.mkdir(parents=True, exist_ok=True)

            # isolation_level=None → autocommit. Транзакцийг зөвхөн
            # `transaction()` эсвэл ганц бичилтийн `_write` удирдана.
            conn = await aiosqlite.connect(self.path, isolation_level=None)
            conn.row_factory = aiosqlite.Row
            await self._configure(conn, read_only=False)
            self._conn = conn

            try:
                await self.migrate()
                if self.path != ":memory:":
                    read = await aiosqlite.connect(self.path, isolation_level=None)
                    read.row_factory = aiosqlite.Row
                    await self._configure(read, read_only=True)
                    self._read_conn = read
            except BaseException:
                if self._read_conn is not None:
                    await self._read_conn.close()
                    self._read_conn = None
                await conn.close()
                self._conn = None
                raise

            log.info("DB холбогдлоо: %s", self.path)
            return self

    @staticmethod
    async def _configure(conn: aiosqlite.Connection, *, read_only: bool) -> None:
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA busy_timeout = 5000")
        await conn.execute("PRAGMA temp_store = MEMORY")
        if read_only:
            # Унших холболтоор санамсаргүй бичихээс DB түвшинд хамгаална.
            await conn.execute("PRAGMA query_only = ON")
            return
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.execute("PRAGMA synchronous = NORMAL")

    async def close(self) -> None:
        if self.in_transaction():
            raise RuntimeError("transaction() дотор Database.close() дуудахгүй.")
        async with self._write_lock:
            read, write = self._read_conn, self._conn
            self._read_conn = None
            self._conn = None
            try:
                if read is not None:
                    await read.close()
            finally:
                if write is not None:
                    await write.close()
            log.info("DB хаагдлаа.")

    async def __aenter__(self) -> Self:
        return await self.connect()

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    # ── Migration ───────────────────────────────────────────────────────
    async def migrate(self) -> None:
        """`migrations/NNN_name.sql` файлуудыг эрэмбээр, нэг л удаа ажиллуулна.

        Файл бүрийн SHA-256 хадгалагдана. Файлыг дараа нь засварлавал дараагийн
        холболт дээр `RuntimeError` — түүхэн migration-ийг өөрчлөхгүй, шинэ
        `NNN_*.sql` нэмнэ. `migrations_dir` өгөөгүй бол migration алгасна.
        """
        if self.migrations_dir is None:
            log.debug("migrations_dir өгөөгүй — migration алгасагдлаа.")
            return
        if not self.migrations_dir.is_dir():
            raise FileNotFoundError(
                f"migrations хавтас олдсонгүй: {self.migrations_dir}"
            )

        files = sorted(
            p
            for p in self.migrations_dir.iterdir()
            if p.is_file() and _MIGRATION_RE.match(p.name)
        )
        if not files:
            raise RuntimeError(f"migration файл олдсонгүй: {self.migrations_dir}")

        disk: dict[int, tuple[Path, str, str]] = {}
        for path in files:
            match = _MIGRATION_RE.match(path.name)
            assert match is not None
            version = int(match.group(1))
            if version in disk:
                raise RuntimeError(f"давхардсан migration version: {version}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            disk[version] = (path, match.group(2), digest)

        async with self._write_lock:
            conn = self._require()
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version     INTEGER PRIMARY KEY,
                    name        TEXT,
                    checksum    TEXT,
                    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            await conn.commit()

            cursor = await conn.execute("PRAGMA table_info(schema_migrations)")
            try:
                columns = {str(row[1]) for row in await cursor.fetchall()}
            finally:
                await cursor.close()
            # Хуучин DB-д name/checksum багана байхгүй.
            if "name" not in columns:
                await conn.execute("ALTER TABLE schema_migrations ADD COLUMN name TEXT")
            if "checksum" not in columns:
                await conn.execute(
                    "ALTER TABLE schema_migrations ADD COLUMN checksum TEXT"
                )
            await conn.commit()

            cursor = await conn.execute(
                "SELECT version, name, checksum FROM schema_migrations"
            )
            try:
                applied = {
                    int(row[0]): (row[1], row[2]) for row in await cursor.fetchall()
                }
            finally:
                await cursor.close()

            missing = set(applied) - set(disk)
            if missing:
                raise RuntimeError(
                    "schema_migrations-д бүртгэгдсэн боловч файл нь байхгүй "
                    f"migration: {sorted(missing)}"
                )

            for version in sorted(disk):
                path, name, digest = disk[version]
                if version in applied:
                    _old_name, old_checksum = applied[version]
                    if old_checksum is None:
                        # Хуучин schema.sql-ээр үүссэн DB: checksum-ийг бөглөнө.
                        await conn.execute(
                            "UPDATE schema_migrations SET name = ?, checksum = ? "
                            "WHERE version = ?",
                            (name, digest, version),
                        )
                        await conn.commit()
                        continue
                    if old_checksum != digest:
                        raise RuntimeError(
                            f"Migration {path.name} өөрчлөгдсөн байна "
                            f"(хадгалсан={old_checksum[:12]}…, одоо={digest[:12]}…). "
                            "Шинэ migration файл нэмнэ үү."
                        )
                    continue

                script = path.read_text(encoding="utf-8")
                try:
                    await conn.executescript(script)
                except BaseException:
                    await self._safe_rollback(conn)
                    try:
                        await conn.execute("PRAGMA foreign_keys = ON")
                    except Exception:
                        log.exception("PRAGMA foreign_keys-ийг сэргээж чадсангүй")
                    raise
                await conn.execute(
                    "INSERT INTO schema_migrations (version, name, checksum) "
                    "VALUES (?, ?, ?)",
                    (version, name, digest),
                )
                await conn.commit()
                log.info("Migration хэрэглэгдлээ: %s", path.name)

    # ── Холболтын сонголт ──────────────────────────────────────────────
    @property
    def connected(self) -> bool:
        return self._conn is not None

    def _require(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database.connect() дуудагдаагүй байна.")
        return self._conn

    def _read_conn_or_main(self) -> aiosqlite.Connection:
        return self._read_conn if self._read_conn is not None else self._require()

    def _current_tx(self) -> _TxState | None:
        state = _tx_state.get()
        if state is None or not state.active or state.db is not self:
            return None
        return state

    def _resolve_write(self) -> aiosqlite.Connection:
        state = self._current_tx()
        if state is not None:
            if state.owner is not asyncio.current_task():
                raise RuntimeError(_LEAKED_TX_MESSAGE)
            return state.conn
        return self._require()

    def _resolve_read(self) -> aiosqlite.Connection:
        state = self._current_tx()
        if state is not None and state.owner is asyncio.current_task():
            return state.conn
        # Өөр task-ийн нээлттэй транзакц байсан ч зөвхөн commit болсон
        # өгөгдлийг тусдаа унших холболтоор уншина.
        return self._read_conn_or_main()

    def in_transaction(self) -> bool:
        """Одоогийн task транзакц эзэмшиж байгаа эсэх."""
        state = _tx_state.get()
        if state is None or not state.active:
            return False
        try:
            return state.owner is asyncio.current_task()
        except RuntimeError:  # event loop-оос гадуур
            return False

    @staticmethod
    async def _safe_rollback(conn: aiosqlite.Connection) -> None:
        try:
            await conn.rollback()
        except Exception:
            log.exception("DB rollback амжилтгүй — холболт түгжигдсэн байж болно.")

    # ── Transaction ────────────────────────────────────────────────────
    @asynccontextmanager
    async def transaction(
        self, *, immediate: bool = True
    ) -> AsyncIterator[aiosqlite.Connection]:
        """Атомик гүйлгээ.

        `immediate=True` нь `BEGIN IMMEDIATE` — бичих зорилготой транзакцад
        SQLITE_BUSY алдааг эрт илрүүлж, түгжээг шууд авна. Зөвхөн уншихад
        `immediate=False` ашиглана.

        Анхаар: транзакц дотор `asyncio.create_task` хийхгүй байх — ContextVar
        нь шинэ task руу тархаж, тэр task бичих үед `RuntimeError` шиднэ.
        """
        state = self._current_tx()
        if state is not None:
            if state.owner is not asyncio.current_task():
                raise RuntimeError(_LEAKED_TX_MESSAGE)
            # Nested — эцэг транзакцад нэгдэнэ, шинээр BEGIN хийхгүй.
            yield state.conn
            return

        async with self._write_lock:
            conn = self._require()
            await conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            state = _TxState(db=self, conn=conn, owner=asyncio.current_task())
            token = _tx_state.set(state)
            try:
                yield conn
            except BaseException:
                state.active = False
                await self._safe_rollback(conn)
                raise
            else:
                try:
                    await conn.commit()
                except BaseException:
                    state.active = False
                    await self._safe_rollback(conn)
                    raise
            finally:
                state.active = False
                _tx_state.reset(token)

    async def _write(
        self, operation: Callable[[aiosqlite.Connection], Awaitable[T]]
    ) -> T:
        """Ганц бичилтийг транзакцад ороож гүйцэтгэнэ.

        Транзакц дотор байгаа бол ижил холболтыг ашиглана; эс бөгөөс
        `_write_lock` авч `BEGIN IMMEDIATE` … `COMMIT` хийнэ. Ингэснээр
        өөр task-ийн нээлттэй транзакцад санамсаргүй нэгдэхгүй.
        """
        state = self._current_tx()
        if state is not None:
            if state.owner is not asyncio.current_task():
                raise RuntimeError(_LEAKED_TX_MESSAGE)
            return await operation(state.conn)

        async with self._write_lock:
            conn = self._require()
            await conn.execute("BEGIN IMMEDIATE")
            try:
                result = await operation(conn)
            except BaseException:
                await self._safe_rollback(conn)
                raise
            else:
                try:
                    await conn.commit()
                except BaseException:
                    await self._safe_rollback(conn)
                    raise
                return result

    # ── Query helpers ──────────────────────────────────────────────────
    async def execute(self, sql: str, params: Params = ()) -> int:
        """Нэг statement гүйцэтгэж, өөрчлөгдсөн мөрийн тоог буцаана."""

        async def operation(conn: aiosqlite.Connection) -> int:
            cursor = await conn.execute(sql, params)
            try:
                return cursor.rowcount
            finally:
                await cursor.close()

        return await self._write(operation)

    async def insert(self, sql: str, params: Params = ()) -> int:
        """INSERT хийж, `lastrowid` буцаана."""

        async def operation(conn: aiosqlite.Connection) -> int:
            cursor = await conn.execute(sql, params)
            try:
                return int(cursor.lastrowid or 0)
            finally:
                await cursor.close()

        return await self._write(operation)

    async def executemany(self, sql: str, seq: Iterable[Params]) -> int:
        rows = list(seq)

        async def operation(conn: aiosqlite.Connection) -> int:
            cursor = await conn.executemany(sql, rows)
            try:
                return cursor.rowcount
            finally:
                await cursor.close()

        return await self._write(operation)

    async def fetchone(self, sql: str, params: Params = ()) -> aiosqlite.Row | None:
        conn = self._resolve_read()
        cursor = await conn.execute(sql, params)
        try:
            return await cursor.fetchone()
        finally:
            await cursor.close()

    async def fetchall(self, sql: str, params: Params = ()) -> list[aiosqlite.Row]:
        conn = self._resolve_read()
        cursor = await conn.execute(sql, params)
        try:
            return list(await cursor.fetchall())
        finally:
            await cursor.close()

    async def fetchval(self, sql: str, params: Params = (), default: Any = None) -> Any:
        row = await self.fetchone(sql, params)
        if row is None:
            return default
        value = row[0]
        return default if value is None else value

    async def fetchval_write(
        self, sql: str, params: Params = (), default: Any = None
    ) -> Any:
        """`UPDATE/INSERT … RETURNING`-ийг бичих холболт дээр гүйцэтгэнэ.

        `fetchval()` нь `query_only` унших холболт ашигладаг тул RETURNING-тэй
        бичих statement-д тохирохгүй. Энэ метод транзакц дотор байвал тухайн
        транзакцад, эс бөгөөс шинэ `BEGIN IMMEDIATE`-д нэгдэнэ.
        """

        async def operation(conn: aiosqlite.Connection) -> Any:
            cursor = await conn.execute(sql, params)
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
            if row is None:
                return default
            value = row[0]
            return default if value is None else value

        return await self._write(operation)
