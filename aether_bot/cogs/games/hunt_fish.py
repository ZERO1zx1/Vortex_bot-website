"""Games Hunt & Fish cog — a!hunt / a!fish."""

from __future__ import annotations

from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_embed
from core.exceptions import AetherError
from ui.embeds import catch_embed


class HuntFish(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    async def _act(self, ctx: commands.Context, service_method) -> None:
        try:
            result = await service_method()
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        await send_embed(ctx, catch_embed(result, ctx.author.display_name))

    @commands.command(name="hunt")
    async def hunt(self, ctx: commands.Context) -> None:
        await self._act(ctx, lambda: self.bot.huntfish.hunt(ctx.author.id))

    @commands.command(name="fish")
    async def fish(self, ctx: commands.Context) -> None:
        await self._act(ctx, lambda: self.bot.huntfish.fish(ctx.author.id))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HuntFish(bot))
