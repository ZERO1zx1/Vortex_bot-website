"""Casino Roulette cog — a!roulette / a!roulette <бооцоо>."""

from __future__ import annotations

from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_embed, send_view
from core.checks import not_jailed
from core.exceptions import AetherError
from ui.casino.roulette_view import RouletteView
from ui.embeds import roulette_embed, start_casino_embed


class Roulette(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="roulette", aliases=["rou"])
    @not_jailed()
    async def roulette(
        self, ctx: commands.Context, bet: str | None = None, bet_type: str = "red"
    ) -> None:
        if bet is not None:
            try:
                result = await self.bot.roulette.play(ctx.author.id, bet, bet_type)
            except AetherError as exc:
                await maybe_error(ctx, exc)
                return
            await send_embed(ctx, roulette_embed(result, ctx.author.display_name))
            return
        view = RouletteView(ctx.author.id, self.bot.roulette, ctx.author.display_name)
        await send_view(
            ctx,
            embed=start_casino_embed("roulette", ctx.author.display_name),
            view=view,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Roulette(bot))
