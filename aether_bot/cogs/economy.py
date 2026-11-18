"""Баланс ба профайлын командууд."""

from __future__ import annotations

import discord
from discord.ext import commands

from cogs._helpers import reply_error
from core.exceptions import AetherError
from ui.embeds import balance_embed


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="balance",
        description="Wallet, bank болон Aether профайлаа харуулна.",
    )
    async def balance(
        self,
        ctx: commands.Context,
        member: discord.Member | None = None,
    ) -> None:
        target = member or ctx.author
        try:
            user = await self.bot.user_repo.get_or_create(target.id)  # type: ignore[attr-defined]
            mods = await self.bot.skills.get_modifiers(target.id)  # type: ignore[attr-defined]
        except AetherError as exc:
            await reply_error(ctx, exc.user_message)
            return
        await ctx.reply(
            embed=balance_embed(user, mods, target.display_name),
            mention_author=False,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economy(bot))
