"""Games Duel cog — a!duel @user <бооцоо>."""

from __future__ import annotations

import discord
from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_view
from core.exceptions import AetherError
from ui.embeds import duel_embed
from ui.games.duel_view import DuelView


class Duel(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="duel", aliases=["d"])
    async def duel(
        self,
        ctx: commands.Context,
        member: discord.Member,
        bet: str = "100",
    ) -> None:
        try:
            state = await self.bot.duel.challenge(ctx.author.id, member.id, bet)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        view = DuelView(
            state,
            self.bot.duel,
            ctx.author.display_name,
            member.display_name,
        )
        await send_view(
            ctx,
            embed=duel_embed(state, ctx.author.display_name, member.display_name),
            view=view,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Duel(bot))
