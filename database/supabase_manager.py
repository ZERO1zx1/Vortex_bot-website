import os
from supabase import create_client, Client
from typing import Any, List, Dict, Optional

class SupabaseManager:
    def __init__(self):
        self.url: str = os.getenv("SUPABASE_URL", "")
        self.key: str = os.getenv("SUPABASE_KEY", "")
        self.client: Optional[Client] = None

    def connect(self) -> Client:
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables.")
        self.client = create_client(self.url, self.key)
        return self.client

    def execute_sync(self, table: str, data: Dict[str, Any]):
        """Sync version of execute."""
        return self.client.table(table).upsert(data).execute()

    async def execute(self, table: str, data: Dict[str, Any]):
        """Insert or update data in a table."""
        # Supabase SDK is synchronous, but we wrap it for async compatibility in cogs
        return self.client.table(table).upsert(data).execute()

    async def fetchone(self, table: str, query_filter: Dict[str, Any]):
        """Fetch a single record from a table."""
        query = self.client.table(table).select("*")
        for key, value in query_filter.items():
            query = query.eq(key, value)
        result = query.limit(1).execute()
        return result.data[0] if result.data else None

    async def fetchall(self, table: str, query_filter: Optional[Dict[str, Any]] = None, order_by: Optional[str] = None, desc: bool = False):
        """Fetch all records from a table."""
        query = self.client.table(table).select("*")
        if query_filter:
            for key, value in query_filter.items():
                query = query.eq(key, value)
        if order_by:
            query = query.order(order_by, desc=desc)
        result = query.execute()
        return result.data

    async def delete(self, table: str, query_filter: Dict[str, Any]):
        """Delete records from a table."""
        query = self.client.table(table).delete()
        for key, value in query_filter.items():
            query = query.eq(key, value)
        return query.execute()

    async def increment(self, table: str, query_filter: Dict[str, Any], column: str, amount: int = 1):
        """Increment a numeric column."""
        # First fetch current value
        row = await self.fetchone(table, query_filter)
        if row:
            current_val = row.get(column, 0)
            new_data = {**query_filter, column: current_val + amount}
            return await self.execute(table, new_data)
        else:
            # If record doesn't exist, create it with the amount
            new_data = {**query_filter, column: amount}
            return await self.execute(table, new_data)

    async def init_tables(self):
        """
        Note: DDL operations (CREATE TABLE) are not supported directly via the Supabase Python SDK.
        Tables should be created via the Supabase Dashboard or the CLI/MCP tool.
        This method is kept for architectural consistency but will log a reminder.
        """
        print("ℹ️ Supabase tables should be pre-configured via Dashboard or Migrations.")
