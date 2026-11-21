"""Cog-уудын нийтлэг туслах."""

from __future__ import annotations

from discord.ext import commands  # type: ignore[attr-defined]

from core.exceptions import AetherError


async def reply_error(ctx: commands.Context, message: str) -> None:
    """Slash дээр ephemeral, prefix дээр энгийн хариу."""
    if ctx.interaction is not None:
        if ctx.interaction.response.is_done():
            await ctx.interaction.followup.send(message, ephemeral=True)
        else:
            await ctx.interaction.response.send_message(message, ephemeral=True)
    else:
        await ctx.reply(message)


async def send_embed(ctx: commands.Context, embed) -> object:
    return await ctx.reply(embed=embed, mention_author=False)


async def send_view(ctx: commands.Context, *, embed, view) -> object:
    message = await ctx.reply(embed=embed, view=view, mention_author=False)
    view.message = message
    return message


async def maybe_error(ctx: commands.Context, exc: AetherError) -> None:
    await reply_error(ctx, exc.user_message)
