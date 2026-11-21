"""Casino Lottery cog — a!lottery [info|buy|draw]."""

from __future__ import annotations

from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_embed, send_view
from core.exceptions import AetherError
from ui.casino.lottery_view import LotteryView
from ui.embeds import lottery_draw_embed, lottery_embed


class Lottery(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="lottery", aliases=["lot"])
    async def lottery(
        self,
        ctx: commands.Context,
        action: str = "info",
        quantity: int = 1,
    ) -> None:
        action = action.lower()
        try:
            if action in {"info", "show", ""}:
                info = await self.bot.lottery.info()
                await send_embed(ctx, lottery_embed(info, ctx.author.display_name))
                return
            if action in {"buy", "tickets"}:
                info = await self.bot.lottery.buy(ctx.author.id, quantity)
                await send_embed(ctx, lottery_embed(info, ctx.author.display_name))
                return
            if action == "draw":
                draw = await self.bot.lottery.draw()
                await send_embed(ctx, lottery_draw_embed(draw))
                return
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        if action == "panel":
            view = LotteryView(ctx.author.id, self.bot.lottery, ctx.author.display_name)
            embed = await view._info_embed()
            await send_view(ctx, embed=embed, view=view)
            return
        await maybe_error(
            ctx,
            AetherError(
                "✦ Usage: `a!lottery` info | `a!lottery buy <quantity>` | `a!lottery draw`."
            ),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Lottery(bot))
