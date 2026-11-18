"""Cog-уудын нийтлэг туслах."""

from __future__ import annotations

from discord.ext import commands


async def reply_error(ctx: commands.Context, message: str) -> None:
    """Slash дээр ephemeral, prefix дээр энгийн хариу."""
    if ctx.interaction is not None:
        if ctx.interaction.response.is_done():
            await ctx.interaction.followup.send(message, ephemeral=True)
        else:
            await ctx.interaction.response.send_message(message, ephemeral=True)
    else:
        await ctx.reply(message)
