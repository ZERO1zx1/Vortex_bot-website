"""Async repository layer over the Supabase Python client.

The official Supabase SDK is synchronous; every query is executed through
``asyncio.to_thread`` so blocking I/O never stalls the Discord event loop.
Legacy ``.acquire()`` / ``.cursor()`` / raw-SQL usage is not allowed.
"""

import asyncio
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

    async def init_tables(self):
        """DDL is handled via Supabase Dashboard / SQL migrations."""
        print("ℹ️ Supabase tables should be pre-configured via Dashboard or Migrations.")

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

    async def increment(self, table: str, filters: Dict[str, Any], column: str, amount: int = 1) -> bool:
        """Atomically increment a numeric column via the ``increment`` RPC.

        Requires the migration in supabase_schema.sql that defines:
            increment(table_name text, filter_col text, filter_val text, col text, delta bigint)
        """
        if not table or not filters or not column:
            return False
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
        except Exception:
            row = await self.fetch_one(table, filters)
            if row:
                current = row.get(column, 0) or 0
                await self.update(table, filters, {column: current + amount})
            else:
                data = dict(filters)
                data[column] = amount
                await self.insert(table, data)
            return True

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