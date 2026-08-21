"""Centralized Discord embed / UI helpers."""

import discord
from discord.ext import commands
from utils.branding import (
    BOT_FOOTER,
    PRIMARY_COLOR,
    SUCCESS_COLOR,
    ERROR_COLOR,
    WARNING_COLOR,
    GOLD_COLOR,
    INFO_COLOR,
)


def brand_embed(title=None, description=None, color=PRIMARY_COLOR, footer=BOT_FOOTER) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    if footer:
        embed.set_footer(text=footer)
    return embed


def success_embed(title=None, description=None, footer=BOT_FOOTER) -> discord.Embed:
    return brand_embed(title=title, description=description, color=SUCCESS_COLOR, footer=footer)


def error_embed(title="Алдаа", description=None, footer=BOT_FOOTER) -> discord.Embed:
    return brand_embed(title=title, description=description, color=ERROR_COLOR, footer=footer)


def warning_embed(title=None, description=None, footer=BOT_FOOTER) -> discord.Embed:
    return brand_embed(title=title, description=description, color=WARNING_COLOR, footer=footer)


def info_embed(title=None, description=None, footer=BOT_FOOTER) -> discord.Embed:
    return brand_embed(title=title, description=description, color=INFO_COLOR, footer=footer)


def gold_embed(title=None, description=None, footer=BOT_FOOTER) -> discord.Embed:
    return brand_embed(title=title, description=description, color=GOLD_COLOR, footer=footer)


def loading_embed(description="Түр хүлээнэ үү...", footer=BOT_FOOTER) -> discord.Embed:
    return info_embed(title="⏳ Ачааллаж байна...", description=description, footer=footer)


async def safe_defer(target, ephemeral=False):
    """Safely defer an interaction or context without raising."""
    if isinstance(target, discord.Interaction):
        if not target.response.is_done():
            try:
                await target.response.defer(ephemeral=ephemeral)
            except discord.InteractionResponded:
                pass
    elif isinstance(target, commands.Context):
        try:
            await target.defer(ephemeral=ephemeral)
        except Exception:
            pass


async def safe_respond(target, content=None, embed=None, view=None, ephemeral=False, delete_after=None):
    """Safely respond to an Interaction or Context, respecting response state."""
    if isinstance(target, discord.Interaction):
        try:
            if target.response.is_done():
                await target.followup.send(content=content, embed=embed, view=view, ephemeral=ephemeral)
            else:
                await target.response.send_message(content=content, embed=embed, view=view, ephemeral=ephemeral)
        except discord.InteractionResponded:
            await target.followup.send(content=content, embed=embed, view=view, ephemeral=ephemeral)
        except discord.HTTPException:
            try:
                await target.followup.send(content=content, embed=embed, view=view, ephemeral=ephemeral)
            except Exception:
                pass
        return

    if isinstance(target, commands.Context):
        kwargs = {}
        if delete_after:
            kwargs["delete_after"] = delete_after
        await target.send(content=content, embed=embed, view=view, **kwargs)
        return

    raise TypeError("Expected discord.Interaction or commands.Context")