"""Async repository layer over the Supabase Python client.

The official Supabase SDK is synchronous; every query is executed through
``asyncio.to_thread`` so blocking I/O never stalls the Discord event loop.
Legacy ``.acquire()`` / ``.cursor()`` / raw-SQL usage is not allowed.
"""

import asyncio
import logging
import os
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, NoReturn, Optional

import httpx
from supabase import create_client, Client
from supabase.lib.client_options import SyncClientOptions

# Network errors that are transient (Windows/Python 3.13 socket flakiness,
# temporary timeouts) and are safe to retry with backoff.
_NETWORK_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)
try:
    from httpx import TransportError
    _NETWORK_EXCEPTIONS = _NETWORK_EXCEPTIONS + (TransportError,)
except ImportError:
    pass

_NETWORK_EXCEPTIONS = tuple({t for t in _NETWORK_EXCEPTIONS})


from src.core.config import pick_server_supabase_key
from src.core.exceptions import (
    DatabaseUnavailableError,
    DatabasePermissionError,
    DatabaseSchemaError,
)

_KNOWN_STATUS_ATTRS = ("http_status", "status_code", "status")


def classify_supabase_error(exc: BaseException) -> BaseException:
    """Map a PostgREST/Supabase failure to a typed application exception.

    Transient failures (network, 5xx) map to :class:`DatabaseUnavailableError`,
    privilege failures (42501) to :class:`DatabasePermissionError`, and missing
    schema (PGRST205 / HTTP 404) to :class:`DatabaseSchemaError`.  Unknown
    errors are returned unchanged so callers can still tell accidents apart
    from expected infrastructure states.
    """
    msg = str(exc)
    code = getattr(exc, "code", None) or ""
    status = next((getattr(exc, a, None) for a in _KNOWN_STATUS_ATTRS
                   if getattr(exc, a, None) is not None), 0)
    try:
        code_str = str(code)
    except Exception:
        code_str = ""
    try:
        status_int = int(status)
    except (TypeError, ValueError):
        status_int = 0

    if "PGRST205" in code_str or "PGRST205" in msg or status_int == 404:
        return DatabaseSchemaError(str(exc))
    if "42501" in code_str or "42501" in msg:
        return DatabasePermissionError(str(exc))
    if _is_retryable(exc) or status_int in (500, 502, 503, 504):
        return DatabaseUnavailableError(str(exc))
    return exc


# Per-table infrastructure-error deduplication window (seconds).
# Keeps "same table unavailable" from flooding the log every event/loop.
_LOG_DEDUP_WINDOW = 600


class _TableErrorTracker:
    """Rate-limits identical infrastructure failures per table.

    First failure logs the full actionable message; repeats within the
    window are counted silently; when the window elapses a compact summary
    (occurrence count in the window) is logged and the window restarts.
    """

    def __init__(self, logger_name: str = "aether.db"):
        self._logger = logging.getLogger(logger_name)
        self._window_start: OrderedDict[str, float] = OrderedDict()
        self._counts: dict[str, int] = {}
        self._last_detail: dict[str, str] = {}
        self._max_tables = 256  # bounded memory

    def _prune(self, now: float):
        expired = [k for k, w in self._window_start.items() if now - w >= _LOG_DEDUP_WINDOW]
        for k in expired:
            self._emit_summary(k)
            self._window_start.pop(k, None)
            self._counts.pop(k, None)
            self._last_detail.pop(k, None)
        # Bound memory if a flood of distinct tables arrives.
        while len(self._window_start) > self._max_tables:
            oldest = next(iter(self._window_start))
            self._window_start.pop(oldest, None)
            self._counts.pop(oldest, None)
            self._last_detail.pop(oldest, None)

    def _emit_summary(self, table: str):
        detail = self._last_detail.get(table, "")
        count = self._counts.get(table, 0)
        self._logger.error(
            "Table '%s' unavailable: %d repeat error(s) in the last %ds. "
            "Fix the database (migrations/grants) to stop this. Last: %s",
            table, count, _LOG_DEDUP_WINDOW, detail,
        )

    def report(self, table: str, detail: str):
        now = time.monotonic()
        start = self._window_start.get(table)
        if start is None:
            self._prune(now)
            self._window_start[table] = now
            self._counts[table] = 0
            self._last_detail[table] = detail
            self._logger.error(
                "Table '%s' unavailable (apply src/database/migrations/20260101_001_initial_schema.sql "
                "and restart): %s", table, detail,
            )
            return
        if now - start >= _LOG_DEDUP_WINDOW:
            self._emit_summary(table)
            self._window_start[table] = now
            self._counts[table] = 0
        self._counts[table] = self._counts.get(table, 0) + 1
        self._last_detail[table] = detail


def _is_retryable(exc: BaseException) -> bool:
    """True when a failure is transient and safe to retry with backoff.

    Covers socket-level network errors (``_NETWORK_EXCEPTIONS``) plus
    PostgREST API failures caused by transient server-side conditions
    (HTTP 5xx, most notably the 504 Gateway Timeout the bot sees when
    Supabase occasionally stalls).  Non-transient errors (4xx, auth,
    missing tables, bad data) are never retried and propagate immediately.
    """
    if isinstance(exc, _NETWORK_EXCEPTIONS):
        return True
    code = getattr(exc, "code", None)
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    try:
        code = int(code)
    except (TypeError, ValueError):
        code = None
    try:
        status = int(status)
    except (TypeError, ValueError):
        status = None
    return code in (500, 502, 503, 504) or status in (500, 502, 503, 504)


class SupabaseManager:
    """Async-first data access layer for Supabase."""

    # Key precedence — anon/publishable key-ээс зайлсхийх (42501).
    # Зөвхөн server-level key (JWT role=service_role эсвэл sb_secret_)
    # сонгогдоно — ``pick_server_supabase_key()`` үүнийг баталгаажуулна.
    # Үлдсэн дараалал нь миграци probe-д ашиглагдана.
    KEY_CANDIDATE_ENVS = (
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_SECRET_KEY",
        "SUPABASE_KEY",
    )

    def __init__(self):
        self.url: str = os.getenv("SUPABASE_URL", "")
        self.key: str = pick_server_supabase_key()
        self.using_legacy_env_name = bool(
            not os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            and not os.getenv("SUPABASE_SECRET_KEY")
            and os.getenv("SUPABASE_KEY")
        )
        self.client: Optional[Client] = None
        self._table_error_tracker = _TableErrorTracker()

    def _pick_first_defined(self) -> str:
        return pick_server_supabase_key()

    def available_keys(self) -> List[Dict[str, str]]:
        """All key env names that have a value, in precedence order."""
        return [
            {"env": env, "key": os.getenv(env, "").strip()}
            for env in self.KEY_CANDIDATE_ENVS
            if os.getenv(env, "").strip()
        ]

    async def probe_best_key(self, probe_table: str = "leveling_config") -> Optional[str]:
        """Find the first key (in precedence order) that can read ``probe_table``.

        Runs at startup after connection so a restricted key is silently
        replaced by the working server key instead of failing every heartbeat
        with 42501.  Returns the env var name of the chosen key, or None if
        nothing works (caller keeps the first key).

        ``bot_status`` is deliberately NOT the probe target: the permission
        migration grants ``SELECT ON bot_status TO anon`` for the website
        heartbeat, so an anon key would pass that probe and the real failure
        (42501 on ``leveling_config``/``shop_stock`` etc.) would stay hidden.
        """
        candidates = self.available_keys()
        if not candidates:
            return None
        current = self._pick_first_defined()

        for cand in candidates:
            key = cand["key"]
            if key == current and self.client is not None:
                # already connected with this key: not a fresh probe target
                pass
            try:
                saved = self.client
                self.client = self._make_client(key)
                try:
                    if await self.probe_table(probe_table) == "OK":
                        return cand["env"]
                finally:
                    self.client = saved
            except Exception:
                continue
        # fall back to the first configured key (log-worthy but non-fatal)
        return candidates[0]["env"]

    def _make_client(self, key: str) -> Client:
        http_client = httpx.Client(
            http1=True,
            http2=False,
            timeout=30.0,
        )
        return create_client(
            self.url,
            key,
            options=SyncClientOptions(httpx_client=http_client),
        )

    # ------------------------------------------------------------------
    # Connection / lifecycle
    # ------------------------------------------------------------------
    def connect(self) -> Client:
        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL and one server key must be set: "
                "SUPABASE_SERVICE_ROLE_KEY, SUPABASE_SECRET_KEY, "
                "or legacy SUPABASE_KEY."
            )
        if self.using_legacy_env_name:
            logging.getLogger("aether.db").warning(
                "SUPABASE_KEY is a deprecated environment name; migrate this "
                "server-side value to SUPABASE_SERVICE_ROLE_KEY or "
                "SUPABASE_SECRET_KEY."
            )
        # Force HTTP/1.1: the httpcore HTTP/2 sync transport is unstable on
        # Windows with Python 3.13 (sporadic [WinError 10035]
        # WSAEWOULDBLOCK socket errors during framing). HTTP/1.1 is reliable.
        self.client = self._make_client(self.key)
        return self.client

    def switch_key(self, env_name: str) -> bool:
        """Swap the active key to another env var's value (for runtime recovery).

        Re-creates the PostgREST client with the new key.  Returns True on
        success; on failure stays on the current key and returns False.
        """
        if not self.url:
            return False
        key = os.getenv(env_name, "").strip()
        if not key:
            logger = logging.getLogger("aether.db")
            logger.warning("switch_key: env '%s' is empty/undefined", env_name)
            return False
        try:
            new_client = self._make_client(key)
        except Exception as exc:
            logger = logging.getLogger("aether.db")
            logger.error("switch_key: failed to build client for '%s': %s", env_name, exc)
            return False
        self.client = new_client
        self.key = key
        logger = logging.getLogger("aether.db")
        logger.info("Supabase key switched to env '%s' (runtime probe)", env_name)
        return True

    def is_connected(self) -> bool:
        return self.client is not None

    async def close(self):
        self.client = None

    REQUIRED_TABLES = [
        "economy", "levels", "giveaways", "temproles", "role_income",
        "tempvoice_setup_msg", "user_inventory",
    ]

    async def init_tables(self):
        """Validate that required tables exist in Supabase.

        Reports missing tables with actionable guidance. Does NOT auto-create
        tables — schema changes should be applied via migrations.
        """
        logger = logging.getLogger("aether.db")
        for table in self.REQUIRED_TABLES:
            exists = await self.table_exists(table)
            if not exists:
                logger.warning(
                    "Required Supabase table '%s' is missing. "
                    "Apply database migration: src/database/migrations/20260101_001_initial_schema.sql",
                    table,
                )
        logger.info("Supabase schema validation complete.")

    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists by attempting a count query."""
        try:
            def _check():
                self.client.table(table_name).select("*", count="exact").limit(0).execute()
            await self._run(_check, _table=table_name)
            return True
        except Exception:
            return False

    async def probe_table(self, table_name: str) -> str:
        """Return a machine-readable health status for ``table_name``.

        Results: ``OK``, ``MISSING`` (PGRST205/404), ``PERMISSION_DENIED``
        (42501), ``UNAVAILABLE`` (network/5xx), or ``ERROR: <reason>`` for
        anything else.  Never raises; safe to call from startup and tools.
        """
        try:
            def _check():
                self.client.table(table_name).select("*", count="exact").limit(0).execute()
            await self._run(_check, _table=table_name)
            return "OK"
        except Exception as e:
            cls = classify_supabase_error(e)
            if isinstance(cls, DatabaseSchemaError):
                return "MISSING"
            if isinstance(cls, DatabasePermissionError):
                return "PERMISSION_DENIED"
            if isinstance(cls, DatabaseUnavailableError):
                return "UNAVAILABLE"
            return f"ERROR: {cls.__class__.__name__}: {e}"

    async def health_check(self, tables: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """Probe every required/critical table and report one status each.

        Used by the startup sequence and the db-health diagnostic tool so a
        broken schema is discovered once, before traffic generates thousands
        of identical tracebacks.
        """
        if tables is None:
            tables = self.REQUIRED_TABLES + [
                "staff_members", "staff_activity", "counting_config",
                "confession_config", "avatar_log_config", "guild_config",
                "greeting_config", "invite_log_config", "user_quests",
                "temp_channels", "work_phrases", "game_stats", "warnings",
            ]
        results: List[Dict[str, str]] = []
        for t in tables:
            results.append({"table": t, "status": await self.probe_table(t)})
        return results

    # ------------------------------------------------------------------
    # Low-level helper
    # ------------------------------------------------------------------
    def _raise_with_hint(self, table: str, exc: BaseException) -> NoReturn:
        """Raise a typed database error with an actionable fix hint.

        42501 (permission denied) becomes :class:`DatabasePermissionError`
        pointing at the repair/GRANT migration; PGRST205 / 42P01 (missing
        table) becomes :class:`DatabaseSchemaError` pointing at the schema
        migrations.  Any other error is re-raised unchanged so unrelated
        failures keep their original meaning.
        """
        msg = str(exc)
        if "42501" in msg:
            raise DatabasePermissionError(
                f"{table}: {msg}\n"
                "Hint: Apply migration src/database/migrations/"
                "20260918_003_repair_permissions.sql and verify the Service "
                "Role key is active (JWT role='service_role')."
            )
        if "PGRST205" in msg or "42P01" in msg:
            raise DatabaseSchemaError(
                f"{table}: {msg}\n"
                "Hint: Apply migrations in order: "
                "20260101_001_initial_schema.sql then "
                "20260813_002_missing_tables.sql."
            )
        raise

    async def _run(self, fn, *args, _table: str = "", **kwargs):
        if self.client is None:
            raise RuntimeError("Supabase client is not connected.")
        # Retry wrapper: transient network errors (e.g. [WinError 10035]) and
        # server-side 5xx responses (e.g. 504 Gateway Timeout from PostgREST)
        # are retried with exponential backoff instead of failing outright.
        attempt = 0
        last_exc = None
        while attempt <= 3:
            try:
                return await asyncio.to_thread(fn, *args, **kwargs)
            except Exception as exc:
                if not _is_retryable(exc):
                    self._raise_with_hint(_table, exc)
                last_exc = exc
                attempt += 1
                if attempt <= 3:
                    await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
                else:
                    break
        raise last_exc

    def table(self, name: str) -> Any:
        if self.client is None:
            raise RuntimeError("Supabase client is not connected.")
        return self.client.table(name)

    async def rpc(self, fn: str, params: Optional[Dict[str, Any]] = None) -> Any:
        def _call():
            return self.client.rpc(fn, params or {}).execute()
        return await self._run(_call, _table=f"rpc:{fn}")

    # ------------------------------------------------------------------
    # Generic queries
    # ------------------------------------------------------------------
    async def fetch_one(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        selects: str = "*",
        order_by: Optional[str] = None,
        desc: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single row as a dict, or None."""
        def _fetch():
            q = self.table(table).select(selects)
            if filters:
                for k, v in filters.items():
                    q = q.eq(k, v)
            if order_by:
                q = q.order(order_by, desc=desc)
            result = q.limit(1).execute()
            return result.data[0] if result.data else None
        return await self._run(_fetch, _table=table)

    async def fetch_all(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        selects: str = "*",
        order_by: Optional[str] = None,
        desc: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch multiple rows as a list of dicts."""
        def _fetch():
            q = self.table(table).select(selects)
            if filters:
                for k, v in filters.items():
                    q = q.eq(k, v)
            if order_by:
                q = q.order(order_by, desc=desc)
            if limit:
                q = q.limit(limit)
            if offset:
                q = q.offset(offset)
            result = q.execute()
            return result.data or []
        return await self._run(_fetch, _table=table)

    async def insert(self, table: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        def _insert():
            result = self.table(table).insert(data).execute()
            d = result.data
            if isinstance(d, bool) or not isinstance(d, list):
                return []
            return d or []
        return await self._run(_insert, _table=table)

    async def update(self, table: str, filters: Dict[str, Any], data: Dict[str, Any]) -> List[Dict[str, Any]]:
        def _update():
            q = self.table(table).update(data)
            for k, v in filters.items():
                q = q.eq(k, v)
            result = q.execute()
            d = result.data
            if isinstance(d, bool) or not isinstance(d, list):
                return []
            return d or []
        return await self._run(_update, _table=table)

    async def upsert(self, table: str, data: Dict[str, Any], on_conflict: Optional[str] = None) -> List[Dict[str, Any]]:
        def _upsert():
            # postgrest >= 2.x: on_conflict is a kwarg of upsert() itself;
            # the returned SyncQueryRequestBuilder has NO .on_conflict() method.
            # on_conflict=None үед kwarg-гүй дуудна (хоосон string алдаа үүсгэж болзошгүй).
            if on_conflict:
                q = self.table(table).upsert(data, on_conflict=on_conflict)
            else:
                q = self.table(table).upsert(data)
            result = q.execute()
            d = result.data
            if isinstance(d, bool) or not isinstance(d, list):
                return []
            return d or []
        return await self._run(_upsert, _table=table)

    async def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        def _delete():
            q = self.table(table).delete()
            for k, v in filters.items():
                q = q.eq(k, v)
            result = q.execute()
            return result.data or []
        return await self._run(_delete, _table=table)

    # Whitelist of tables/columns allowed for atomic increment via RPC.
    _INCREMENT_WHITELIST = {
        "economy": {"balance", "bank_balance"},
        "levels": {"xp", "message_count", "voice_seconds", "reaction_count"},
        "game_stats": {"wins", "losses", "total_won", "total_bet"},
        "shop_stock": {"current_stock"},
        "user_inventory": {"quantity"},
        "counting_stats": {"correct", "wrong", "saves", "strikes", "best_streak"},
        "counting_progress": {"current_count", "streak"},
        "invite_stats": {"regular", "bonus", "fake", "left"},
        "daily_stats": {"joins", "leaves"},
        "staff_activity": {"messages", "voice_seconds", "tickets_closed", "actions"},
        "user_drunk": {"level"},
        "marriages": {"love_points"},
        "lottery": {"pool"},
        "lottery_entries": {"tickets"},
    }

    async def increment(self, table: str, filters: Dict[str, Any], column: str, amount: int = 1) -> bool:
        """Atomically increment a numeric column via the ``increment`` RPC.

        Requires the migration in supabase_schema.sql that defines:
            increment(table_name text, filter_col text, filter_val text, col text, delta bigint)

        Only whitelisted table/column combinations are allowed to prevent
        arbitrary dynamic SQL abuse.  If the RPC fails the error is logged
        and re-raised — no silent non-atomic fallback.
        """
        if not table or not filters or not column:
            return False

        allowed = self._INCREMENT_WHITELIST.get(table)
        if allowed is None:
            raise ValueError(f"increment() is not allowed for table '{table}'")
        if column not in allowed:
            raise ValueError(f"increment() is not allowed for column '{column}' on table '{table}'")

        filter_col, filter_val = next(iter(filters.items()))

        def _call():
            return self.client.rpc(
                "increment",
                {
                    "table_name": table,
                    "filter_col": filter_col,
                    "filter_val": str(filter_val),
                    "col": column,
                    "delta": int(amount),
                },
            ).execute()

        try:
            await self._run(_call, _table=table)
            return True
        except Exception as e:
            import logging
            logging.getLogger("aether.db").error(
                "increment() RPC failed for %s.%s (filter=%s=%s, delta=%s): %s",
                table, column, filter_col, filter_val, amount, e,
            )
            raise

    # ------------------------------------------------------------------
    # Missing-table-safe reads
    # ------------------------------------------------------------------
    def _is_missing_table(self, error: BaseException) -> bool:
        """True when the error means the table is not in the Supabase
        schema cache (PGRST205), the REST endpoint returned 404, or the
        role lacks privileges on the table (42501 permission denied).

        42501 is treated here because a privilege problem on a *known*
        table always indicates a database setup issue that should be
        fixed by re-applying the migration (GRANT block), not by
        crashing every background loop that reads the table.
        """
        msg = str(error)
        code = getattr(error, "code", None) or ""
        status = getattr(error, "status_code", None) or getattr(error, "status", None) or 0
        return ("PGRST205" in code or "PGRST205" in msg
                or int(status) == 404
                or "42501" in code or "42501" in msg)

    async def fetch_safe(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        single: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Read from ``table`` without raising when the table is missing.

        If the table does not exist in the live Supabase project the call
        logs once at ERROR level and returns ``[]`` (or ``None`` for
        single-row reads) so background tasks keep running instead of
        crashing.  Errors treated as "table unavailable" are:
        PGRST205 (missing table), HTTP 404, and 42501 (permission denied).
        All other errors (auth, network, bad data) still propagate to
        the caller.
        """
        try:
            if single:
                return await self.fetch_one(table, filters or {}, **kwargs)
            return await self.fetch_all(table, filters or {}, **kwargs)
        except Exception as e:
            if not self._is_missing_table(e):
                raise
            self._table_error_tracker.report(table, str(e) or e.__class__.__name__)
            return None if single else []

    # ------------------------------------------------------------------
    # Backward-compatible aliases (shorten migration of older cogs)
    # ------------------------------------------------------------------
    async def execute_sync(self, table: str, data: Dict[str, Any]):
        return await self.upsert(table, data)

    async def fetchone(self, table: str, query_filter: Dict[str, Any]):
        return await self.fetch_one(table, query_filter)

    async def fetchall(self, table: str, query_filter: Optional[Dict[str, Any]] = None, order_by: Optional[str] = None, desc: bool = False):
        return await self.fetch_all(table, query_filter, order_by=order_by, desc=desc)

    async def execute(self, table: str, data: Dict[str, Any]):
        return await self.upsert(table, data)

    # ------------------------------------------------------------------
    # Bot heartbeat (website status page)
    # ------------------------------------------------------------------
    async def ping_bot(self, status: str = "online") -> bool:
        """Update the bot_status row (id=1) with current status and timestamps.

        Keeps the website status page accurate without a dedicated backend:
        the bot writes ``last_ping`` and ``uptime_since`` directly to Supabase,
        and the static site reads them with the anon key.
        """
        try:
            now = datetime.now(timezone.utc).isoformat()
            data: Dict[str, Any] = {"id": 1, "status": status, "last_ping": now}

            def _ping():
                # postgrest 2.x upsert() defaults to merge-duplicates;
                # only write uptime_since on the first ping (when row absent)
                raw = self.table("bot_status").select("uptime_since").eq("id", 1).execute().data
                existing = raw if isinstance(raw, list) else []
                payload = dict(data)
                if not existing or not existing[0].get("uptime_since"):
                    payload["uptime_since"] = now
                try:
                    result = self.table("bot_status").upsert(payload, on_conflict="id").execute()
                    d = result.data
                    return d if isinstance(d, list) else []
                except Exception:
                    # Fallback: row already exists with uptime_since — update status/last_ping only
                    result = (
                        self.table("bot_status")
                        .update({"status": status, "last_ping": now})
                        .eq("id", 1)
                        .execute()
                    )
                    d = result.data
                    return d if isinstance(d, list) else []

            return bool(await self._run(_ping, _table="bot_status"))
        except Exception as exc:  # noqa: BLE001
            reason = classify_supabase_error(exc)
            logging.getLogger("aether.db").warning(
                "Heartbeat failed: %s: %s", type(reason).__name__, exc
            )
            return False
