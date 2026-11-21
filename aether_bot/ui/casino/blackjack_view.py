"""Blackjack view — Hit / Stand / Double / Again."""

from __future__ import annotations

import logging
from typing import Any

import discord

from services.casino.blackjack_service import BlackjackService, BlackjackState

log = logging.getLogger(__name__)
from ui.common.base import AetherView, refresh_panel
from ui.common.modals import BetModal
from ui.embeds import blackjack_embed


class BlackjackView(AetherView):
    def __init__(
        self,
        author_id: int,
        service: BlackjackService,
        state: BlackjackState,
        display_name: str,
    ) -> None:
        super().__init__(author_id, timeout=300.0)
        self.service = service
        self.state = state
        self.display_name = display_name
        self._sync()

    def _sync(self) -> None:
        active = self.state.status == "active"
        self.hit_button.disabled = not active
        self.stand_button.disabled = not active
        self.double_button.disabled = active and len(self.state.player_cards) != 2
        self.again_button.disabled = active

    async def _update_panel(self, interaction: discord.Interaction) -> None:
        self._sync()
        await refresh_panel(
            interaction,
            embed=blackjack_embed(self.state, self.display_name),
            view=self,
        )

    @discord.ui.button(
        label="🃏 Нэмэх",
        style=discord.ButtonStyle.success,
        custom_id="blackjack_hit",
    )
    async def hit_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        self.state = await self.service.hit(interaction.user.id, self.state.game_id)
        await self._update_panel(interaction)

    @discord.ui.button(
        label="⏸️ Орлох",
        style=discord.ButtonStyle.primary,
        custom_id="blackjack_stand",
    )
    async def stand_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        self.state = await self.service.stand(interaction.user.id, self.state.game_id)
        await self._update_panel(interaction)

    @discord.ui.button(
        label="🍀 Double",
        style=discord.ButtonStyle.danger,
        custom_id="blackjack_double",
    )
    async def double_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        self.state = await self.service.double(interaction.user.id, self.state.game_id)
        await self._update_panel(interaction)

    @discord.ui.button(
        label="🎯 Дахин",
        style=discord.ButtonStyle.success,
        custom_id="blackjack_again",
        row=1,
    )
    async def again_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        async def submit(it: discord.Interaction, value: str) -> None:
            state = await self.service.start(it.user.id, value)
            self.state = state
            await self._update_panel(it)

        await interaction.response.send_modal(
            BetModal(game="Blackjack", callback=submit)
        )

    async def on_timeout(self) -> None:
        if self.state.status == "active":
            try:
                self.state = await self.service.stand(
                    self.author_id, self.state.game_id
                )
            except Exception as exc:
                log.debug("Blackjack timeout stand амжилтгүй", exc_info=exc)
        await super().on_timeout()
