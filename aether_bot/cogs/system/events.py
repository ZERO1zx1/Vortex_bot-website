"""System events — Chat XP, app-command error handling."""

from __future__ import annotations

import logging
import time
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

import config
from cogs._bot_types import AetherBotProtocol
from core.event_bus import XPGained
from core.exceptions import AetherError
from ui.common.base import respond_error

log = logging.getLogger(__name__)


def _display_name(message: discord.Message) -> str:
    return message.author.display_name or str(message.author)


class SystemEvents(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]
        self.event_xp_cache: dict[int, float] = {}

    async def cog_load(self) -> None:
        self.bot.tree.on_error = self.on_app_error

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return
        if not message.content.strip():
            return
        user_id = message.author.id
        now = time.monotonic()
        last = self.event_xp_cache.get(user_id, 0.0)
        if now - last < config.XP_MESSAGE_COOLDOWN_SEC:
            return
        self.event_xp_cache[user_id] = now
        await self.bot.event_bus.publish(
            XPGained(
                user_id=user_id,
                amount=config.XP_PER_MESSAGE,
                source="chat",
            )
        )

    async def on_command_error(self, ctx: commands.Context, error: Any) -> None:
        # Check failures тэлж байгаа бол dangling DB/service error биш.
        if isinstance(error, commands.CheckFailure):
            return
        # Үүндээсыг тогтооно, гаднаас ирсэн runtime error-гамшигтай харуулахын бүртгэхгүй.
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, AetherError):
            await ctx.reply(error.user_message, ephemeral=True)
            return
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(getattr(error, "message", "") or str(error), ephemeral=True)
            return
        if isinstance(error, commands.BadArgument):
            await ctx.reply(
                f"✦ Командын хүлээлт: {getattr(error, 'message', '') or error}",
                ephemeral=True,
            )
            return
        log.exception("Command error", exc_info=error)
        await ctx.reply("✦ Ямар нэгэн зүйл буруугаар эргэлдлээ.", ephemeral=True)

    async def on_app_error(self, interaction: discord.Interaction, error: Any) -> None:
        if isinstance(error, app_commands.CheckFailure):
            await respond_error(interaction, error)
            return
        if isinstance(error, AetherError):
            await respond_error(interaction, error)
            return
        log.exception("App command error", exc_info=error)
        await respond_error(
            interaction, AetherError("✦ Ямар нэгэн зүйл буруугаар эргэлдлээ.")
        )

    async def shutdown(self) -> None:
        self.event_xp_cache.clear()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SystemEvents(bot))
