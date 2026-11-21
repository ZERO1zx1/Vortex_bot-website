"""Crash view — үржүүлэгч өснө гүнөрхүү Cashout."""

from __future__ import annotations

import logging
from typing import Any

import discord

from services.casino.crash_service import CrashService, CrashState
from ui.common.base import AetherView, refresh_panel
from ui.common.modals import BetModal
from ui.embeds import crash_embed

log = logging.getLogger(__name__)


class CrashView(AetherView):
    def __init__(
        self,
        author_id: int,
        service: CrashService,
        display_name: str,
        state: CrashState | None = None,
    ) -> None:
        super().__init__(author_id, timeout=120.0)
        self.service = service
        self.display_name = display_name
        self.state = state
        self._sync()

    def _sync(self) -> None:
        active = self.state is not None and self.state.active
        self.start_button.disabled = active
        self.cashout_button.disabled = not active
        self.again_button.disabled = not active

    async def _start_or_again(
        self, interaction: discord.Interaction, value: str
    ) -> None:
        state = await self.service.start(interaction.user.id, value)
        self.state = state
        self._sync()
        await refresh_panel(
            interaction, embed=crash_embed(state, self.display_name), view=self
        )

    async def _cashout(self, interaction: discord.Interaction) -> None:
        if self.state is None:
            return
        state = await self.service.cashout(interaction.user.id, self.state.game_id)
        self.state = state
        self._sync()
        await refresh_panel(
            interaction, embed=crash_embed(state, self.display_name), view=self
        )

    async def on_timeout(self) -> None:
        if self.state is not None and self.state.active:
            try:
                state = await self.service.cashout(self.author_id, self.state.game_id)
                self.state = state
            except Exception as exc:
                log.debug("Crash timeout бүтэхгүй", exc_info=exc)
        await super().on_timeout()

    @discord.ui.button(
        label="🚀 Start",
        style=discord.ButtonStyle.success,
        custom_id="crash_start",
    )
    async def start_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        async def submit(it: discord.Interaction, value: str) -> None:
            await self._start_or_again(it, value)

        await interaction.response.send_modal(BetModal(game="Crash", callback=submit))

    @discord.ui.button(
        label="💸 Cashout",
        style=discord.ButtonStyle.primary,
        custom_id="crash_cashout",
    )
    async def cashout_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self._cashout(interaction)

    @discord.ui.button(
        label="🔁 Again",
        style=discord.ButtonStyle.secondary,
        custom_id="crash_again",
        row=1,
    )
    async def again_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self.start_button.callback(interaction)
