"""Casino Slots cog — a!slots / a!slots <бооцоо>."""

from __future__ import annotations

from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_view
from core.exceptions import AetherError
from ui.casino.slots_view import SlotsView
from ui.embeds import slots_embed, start_casino_embed


class Slots(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="slots", aliases=["s"])
    async def slots(self, ctx: commands.Context, bet: str | None = None) -> None:
        if bet is None:
            view = SlotsView(ctx.author.id, self.bot.slots, ctx.author.display_name)
            await send_view(
                ctx,
                embed=start_casino_embed("slots", ctx.author.display_name),
                view=view,
            )
            return
        try:
            result = await self.bot.slots.spin(ctx.author.id, bet)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        view = SlotsView(ctx.author.id, self.bot.slots, ctx.author.display_name)
        await send_view(
            ctx,
            embed=slots_embed(result, ctx.author.display_name),
            view=view,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Slots(bot))
