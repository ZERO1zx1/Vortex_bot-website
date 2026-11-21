"""Wallet cog — balance/deposit/withdraw/transfer (зөвхөн prefix)."""

from __future__ import annotations

import discord
from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_embed, send_view
from core.exceptions import AetherError
from ui.economy.balance_view import BalanceView
from ui.embeds import (
    balance_embed,
    deposit_embed,
    transfer_embed,
    withdraw_embed,
)


class Wallet(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="balance", aliases=["bal"])
    async def balance(
        self, ctx: commands.Context, member: discord.Member | None = None
    ) -> None:
        target = member or ctx.author
        try:
            user = await self.bot.wallet.balance(target.id)
            mods = await self.bot.skills.get_modifiers(target.id)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        embed = balance_embed(user, mods, target.display_name)
        if target == ctx.author:
            view = BalanceView(
                ctx.author.id, self.bot.wallet, self.bot.skills, target.display_name
            )
            await send_view(ctx, embed=embed, view=view)
        else:
            await send_embed(ctx, embed)

    @commands.command(name="deposit", aliases=["dep"])
    async def deposit(self, ctx: commands.Context, amount: str) -> None:
        try:
            result = await self.bot.wallet.deposit(ctx.author.id, amount)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        await send_embed(ctx, deposit_embed(result, ctx.author.display_name))

    @commands.command(name="withdraw", aliases=["wd"])
    async def withdraw(self, ctx: commands.Context, amount: str) -> None:
        try:
            result = await self.bot.wallet.withdraw(ctx.author.id, amount)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        await send_embed(ctx, withdraw_embed(result, ctx.author.display_name))

    @commands.command(name="transfer", aliases=["pay"])
    async def transfer(
        self,
        ctx: commands.Context,
        member: discord.Member,
        amount: str,
    ) -> None:
        try:
            guild_id = ctx.guild.id if ctx.guild is not None else None
            result = await self.bot.wallet.transfer(
                ctx.author.id, member.id, amount, guild_id=guild_id
            )
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        await send_embed(
            ctx, transfer_embed(result, ctx.author.display_name, member.id)
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Wallet(bot))
