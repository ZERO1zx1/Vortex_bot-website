"""Casino Coinflip cog — a!coinflip / a!coinflip <бооцоо> [heads|tails]."""

from __future__ import annotations

import discord
from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_embed, send_view
from core.exceptions import AetherError
from ui.casino.panel import BetPanelView
from ui.embeds import coinflip_embed, start_casino_embed


class Coinflip(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    async def _submit(self, interaction: discord.Interaction, value: str) -> None:
        result = await self.bot.coinflip.flip(interaction.user.id, value, "heads")
        await interaction.response.edit_message(
            embed=coinflip_embed(result, interaction.user.display_name)
        )

    @commands.command(name="coinflip", aliases=["cf"])
    async def coinflip(
        self,
        ctx: commands.Context,
        bet: str | None = None,
        choice: str = "heads",
    ) -> None:
        if bet is None:
            view = BetPanelView(ctx.author.id, "Coinflip", self._submit)
            await send_view(
                ctx,
                embed=start_casino_embed("coinflip", ctx.author.display_name),
                view=view,
            )
            return
        try:
            result = await self.bot.coinflip.flip(ctx.author.id, bet, choice)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        await send_embed(ctx, coinflip_embed(result, ctx.author.display_name))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Coinflip(bot))
