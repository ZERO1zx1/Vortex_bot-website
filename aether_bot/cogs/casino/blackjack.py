"""Casino Blackjack cog — a!blackjack / a!blackjack <бооцоо>."""

from __future__ import annotations

import discord
from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_view
from core.checks import not_jailed
from core.exceptions import AetherError
from ui.casino.blackjack_view import BlackjackView
from ui.casino.panel import BetPanelView
from ui.common.base import refresh_panel
from ui.embeds import blackjack_embed, start_casino_embed


class Blackjack(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    async def _start(self, interaction: discord.Interaction, value: str) -> None:
        state = await self.bot.blackjack.start(interaction.user.id, value)
        view = BlackjackView(
            interaction.user.id,
            self.bot.blackjack,
            state,
            interaction.user.display_name,
        )
        await refresh_panel(
            interaction,
            embed=blackjack_embed(state, interaction.user.display_name),
            view=view,
        )

    @commands.command(name="blackjack", aliases=["bj"])
    @not_jailed()
    async def blackjack(self, ctx: commands.Context, bet: str | None = None) -> None:
        if bet is None:
            panel = BetPanelView(ctx.author.id, "Blackjack", self._start)
            await send_view(
                ctx,
                embed=start_casino_embed("blackjack", ctx.author.display_name),
                view=panel,
            )
            return
        try:
            state = await self.bot.blackjack.start(ctx.author.id, bet)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        view = BlackjackView(
            ctx.author.id,
            self.bot.blackjack,
            state,
            ctx.author.display_name,
        )
        await send_view(
            ctx,
            embed=blackjack_embed(state, ctx.author.display_name),
            view=view,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Blackjack(bot))
