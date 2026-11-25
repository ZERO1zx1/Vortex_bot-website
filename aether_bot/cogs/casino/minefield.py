"""Casino Minefield cog — a!minefield / a!minefield <бооцоо>."""

from __future__ import annotations

import discord
from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_view
from core.checks import not_jailed
from core.exceptions import AetherError
from ui.casino.minefield_view import MinefieldView
from ui.casino.panel import BetPanelView
from ui.common.base import refresh_panel
from ui.embeds import minefield_embed, start_casino_embed


class Minefield(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    async def _start(self, interaction: discord.Interaction, value: str) -> None:
        state = await self.bot.minefield.start(interaction.user.id, value)
        view = MinefieldView(
            interaction.user.id,
            self.bot.minefield,
            state,
            interaction.user.display_name,
        )
        await refresh_panel(
            interaction,
            embed=minefield_embed(state, interaction.user.display_name),
            view=view,
        )

    @commands.command(name="minefield", aliases=["mf"])
    @not_jailed()
    async def minefield(self, ctx: commands.Context, bet: str | None = None) -> None:
        if bet is None:
            panel = BetPanelView(ctx.author.id, "Minefield", self._start)
            await send_view(
                ctx,
                embed=start_casino_embed("minefield", ctx.author.display_name),
                view=panel,
            )
            return
        try:
            state = await self.bot.minefield.start(ctx.author.id, bet)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        view = MinefieldView(
            ctx.author.id,
            self.bot.minefield,
            state,
            ctx.author.display_name,
        )
        await send_view(
            ctx,
            embed=minefield_embed(state, ctx.author.display_name),
            view=view,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Minefield(bot))
