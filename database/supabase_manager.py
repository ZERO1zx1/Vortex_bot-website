"""Async repository layer over the Supabase Python client.

The official Supabase SDK is synchronous; every query is executed through
``asyncio.to_thread`` so blocking I/O never stalls the Discord event loop.
Legacy ``.acquire()`` / ``.cursor()`` / raw-SQL usage is not allowed.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from supabase import create_client, Client


class SupabaseManager:
    """Async-first data access layer for Supabase."""

    def __init__(self):
        self.url: str = os.getenv("SUPABASE_URL", "")
        self.key: str = os.getenv("SUPABASE_KEY", "")
        self.client: Optional[Client] = None

    # ------------------------------------------------------------------
    # Connection / lifecycle
    # ------------------------------------------------------------------
    def connect(self) -> Client:
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables.")
        self.client = create_client(self.url, self.key)
        return self.client

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
                    "Apply database migration: database/migrations/000_complete_schema.sql",
                    table,
                )
        logger.info("Supabase schema validation complete.")

    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists by attempting a count query."""
        try:
            def _check():
                self.client.table(table_name).select("*", count="exact").limit(0).execute()
            await self._run(_check)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Low-level helper
    # ------------------------------------------------------------------
    async def _run(self, fn, *args, **kwargs):
        if self.client is None:
            raise RuntimeError("Supabase client is not connected.")
        return await asyncio.to_thread(fn, *args, **kwargs)

    def table(self, name: str) -> Any:
        if self.client is None:
            raise RuntimeError("Supabase client is not connected.")
        return self.client.table(name)

    async def rpc(self, fn: str, params: Optional[Dict[str, Any]] = None) -> Any:
        def _call():
            return self.client.rpc(fn, params or {}).execute()
        return await self._run(_call)

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
        return await self._run(_fetch)

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
        return await self._run(_fetch)

    async def insert(self, table: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        def _insert():
            result = self.table(table).insert(data).execute()
            return result.data or []
        return await self._run(_insert)

    async def update(self, table: str, filters: Dict[str, Any], data: Dict[str, Any]) -> List[Dict[str, Any]]:
        def _update():
            q = self.table(table).update(data)
            for k, v in filters.items():
                q = q.eq(k, v)
            result = q.execute()
            return result.data or []
        return await self._run(_update)

    async def upsert(self, table: str, data: Dict[str, Any], on_conflict: Optional[str] = None) -> List[Dict[str, Any]]:
        def _upsert():
            q = self.table(table).upsert(data)
            if on_conflict:
                q = q.on_conflict(on_conflict)
            result = q.execute()
            return result.data or []
        return await self._run(_upsert)

    async def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        def _delete():
            q = self.table(table).delete()
            for k, v in filters.items():
                q = q.eq(k, v)
            result = q.execute()
            return result.data or []
        return await self._run(_delete)

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
            await self._run(_call)
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
        schema cache (PGRST205) or the REST endpoint returned 404."""
        msg = str(error)
        code = getattr(error, "code", None) or ""
        status = getattr(error, "status_code", None) or getattr(error, "status", None) or 0
        return "PGRST205" in code or "PGRST205" in msg or int(status) == 404

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
        crashing.  All other errors (auth, network, bad data) still
        propagate to the caller.
        """
        try:
            if single:
                return await self.fetch_one(table, filters or {}, **kwargs)
            return await self.fetch_all(table, filters or {}, **kwargs)
        except Exception as e:
            if not self._is_missing_table(e):
                raise
            logging.getLogger("aether.db").error(
                "Table '%s' is missing in Supabase (PGRST205). "
                "Apply database/migrations/000_complete_schema.sql and restart.",
                table,
            )
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