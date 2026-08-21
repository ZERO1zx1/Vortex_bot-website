import discord
from discord.ext import commands
from typing import Any, Dict, List, Optional

class SupabaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    async def get_data(self, table: str, query_filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return await self.db.fetchone(table, query_filter)

    async def get_all_data(self, table: str, query_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return await self.db.fetchall(table, query_filter)

    async def update_data(self, table: str, data: Dict[str, Any]):
        return await self.db.execute(table, data)

    async def delete_data(self, table: str, query_filter: Dict[str, Any]):
        return await self.db.delete(table, query_filter)
