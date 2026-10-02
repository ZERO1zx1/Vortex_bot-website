from typing import Any

from discord.ext import commands


class SupabaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    async def get_data(self, table: str, query_filter: dict[str, Any]) -> dict[str, Any] | None:
        return await self.db.fetchone(table, query_filter)

    async def get_all_data(self, table: str, query_filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return await self.db.fetchall(table, query_filter)

    async def update_data(self, table: str, data: dict[str, Any]):
        return await self.db.execute(table, data)

    async def delete_data(self, table: str, query_filter: dict[str, Any]):
        return await self.db.delete(table, query_filter)
