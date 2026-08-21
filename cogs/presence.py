"""
presence.py — 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 bot presence / status management.

Rotating activity statuses (watching / listening / playing / competing)
so the bot looks alive and shows its feature range under its name.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import discord

from discord.ext import commands

if TYPE_CHECKING:
    from main import MyBot

logger = logging.getLogger("bot.presence")

# (activity_type, display_text) pairs shown under the bot name
# i18n friendly: short labels that work in both MN and EN
ACTIVITIES: list[tuple[discord.ActivityType, str]] = [
    (discord.ActivityType.playing, "𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹"),
    (discord.ActivityType.listening, "A!help"),
    (discord.ActivityType.watching, "蒼穹 тэнгэрийн дор"),
    (discord.ActivityType.competing, "A!mafia"),
    (discord.ActivityType.listening, "A!daily"),
    (discord.ActivityType.watching, "A!rank"),
    (discord.ActivityType.playing, "A!gamble"),
    (discord.ActivityType.watching, f"{len([])} гишүүд..."),  # updated at runtime
]

# Placeholder — replaced after ready() with real member count
_MEMBER_WATCH = 6  # index in ACTIVITIES ("... members" entry)


def _sync_lang(gid: str) -> str:
    """Blocking wrapper around get_guild_lang for to_thread."""
    import asyncio
    from utils.i18n import get_guild_lang  # noqa: WPS433

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(get_guild_lang(gid))
    finally:
        loop.close()


class PresenceCog(commands.Cog):
    """Rotates the bot's status every 2 minutes; updates member count watch."""

    def __init__(self, bot: "MyBot") -> None:
        self.bot = bot
        self._current = 0
        self._cycle_started = False

    # ---------------------------------------------------------------
    # on_ready: initial presence set here (bot event)
    # ---------------------------------------------------------------
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Set the first status and start the rotation loop once."""
        if self._cycle_started:
            return
        self._cycle_started = True
        await self._refresh_member_watch()
        await self._set(0)
        self._rotate_task = self.bot.loop.create_task(self._rotate())
        logger.info("🌐 Presence rotation started (%d activities)", len(ACTIVITIES))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Keep the watch status in sync with member changes."""
        if not self._cycle_started:
            return
        await self._refresh_member_watch()

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if not self._cycle_started:
            return
        await self._refresh_member_watch()

    # ---------------------------------------------------------------
    # helpers
    # ---------------------------------------------------------------
    async def _refresh_member_watch(self) -> None:
        """Point the 'watching' activity at the real server member count."""
        if not self.bot.guilds:
            return
        guild = self.bot.guilds[0]  # single-server private bot
        count = guild.member_count or 0
        # Build a short localized watch text (MN/EN based on guild lang)
        text = f"{count:,} гишүүд"
        try:
            from utils.i18n import get_guild_lang, t_direct  # noqa: WPS433
            import asyncio as _asyncio

            lang = await _asyncio.to_thread(lambda: _sync_lang(str(guild.id)))
            text = t_direct(lang, "presence.watchers", count=count)
        except Exception:  # noqa: BLE001
            text = f"{count:,} members"
        ACTIVITIES[_MEMBER_WATCH] = (discord.ActivityType.watching, text)
        # If we are currently showing this slot, re-apply it
        if self._current == _MEMBER_WATCH and self.bot.user is not None:
            await self._set(_MEMBER_WATCH)

    async def _set(self, index: int) -> None:
        kind, text = ACTIVITIES[index]
        await self.bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(type=kind, name=text),
        )

    async def _rotate(self) -> None:
        """Cycle through ACTIVITIES every 120 seconds, forever."""
        while not self.bot.is_closed():
            await asyncio.sleep(120)
            if self.bot.is_closed():
                break
            self._current = (self._current + 1) % len(ACTIVITIES)
            try:
                await self._set(self._current)
            except Exception:  # noqa: BLE001
                logger.warning("⚠️ Presence rotation error", exc_info=True)

    async def cog_unload(self) -> None:
        """Docs extension-teardown best practice: cancel background tasks."""
        if getattr(self, "_rotate_task", None):
            self._rotate_task.cancel()
            try:
                await self._rotate_task
            except asyncio.CancelledError:
                pass


async def setup(bot: "MyBot") -> None:
    await bot.add_cog(PresenceCog(bot))
