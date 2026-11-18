"""Эрүүл мэндийн шалгалт."""

from __future__ import annotations

from discord.ext import commands


class Health(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Ботын latency-г шалгана.")
    async def ping(self, ctx: commands.Context) -> None:
        latency = round(self.bot.latency * 1000)
        await ctx.reply(f"🏓 Pong — **{latency} ms**")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Health(bot))
