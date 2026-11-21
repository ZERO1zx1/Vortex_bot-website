"""Энгийн Бооцоогоо тавих Panel View (interactive slot дугаарыг араар нь)."""

from __future__ import annotations

from typing import Any

import discord

from ui.common.base import AetherView
from ui.common.modals import BetModal


class BetPanelView(AetherView):
    """Бооцоо бичилгүйгээр panel харуулж, товчоор бооцоогоо тавина."""

    def __init__(
        self,
        author_id: int,
        game: str,
        callback: object,
        *,
        label: str = "🎰 Бооцоогоо тавих",
        row: int | None = None,
    ) -> None:
        super().__init__(author_id, timeout=60.0)
        self.game = game
        self._callback = callback
        self._label = label
        self._row = row
        self.start.row = row  # type: ignore[union-attr]

    @discord.ui.button(
        label="🎰 Бооцоогоо тавих",
        style=discord.ButtonStyle.success,
        custom_id="casino_bet_panel",
    )
    async def start(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await interaction.response.send_modal(
            BetModal(game=self.game, callback=self._callback)  # type: ignore[arg-type]
        )
