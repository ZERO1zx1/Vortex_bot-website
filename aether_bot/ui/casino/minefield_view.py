"""Minefield view — 4×4 бөмбөгтэй адшийн tile button-ууд."""

from __future__ import annotations

import logging
from typing import Any

import discord

from services.casino.minefield_service import MinefieldService, MinefieldState

log = logging.getLogger(__name__)
from ui.common.base import AetherView, refresh_panel
from ui.common.modals import BetModal
from ui.embeds import minefield_embed


class MinefieldView(AetherView):
    def __init__(
        self,
        author_id: int,
        service: MinefieldService,
        state: MinefieldState,
        display_name: str,
    ) -> None:
        super().__init__(author_id, timeout=900.0)
        self.service = service
        self.state = state
        self.display_name = display_name
        self._tiles: list[discord.ui.Button[Any]] = []
        for row in range(4):
            for col in range(4):
                tile = row * 4 + col
                button: discord.ui.Button[Any] = discord.ui.Button(
                    label=str(tile + 1),
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"minefield_{tile}",
                    row=row,
                )
                button.callback = self._make_reveal(tile)  # type: ignore[method-assign]
                self._tiles.append(button)
                self.add_item(button)
        self.cashout_button: discord.ui.Button[Any] = discord.ui.Button(
            label="💣 Бооцоо",
            style=discord.ButtonStyle.primary,
            custom_id="minefield_cashout",
            row=4,
        )
        self.cashout_button.callback = self._on_cashout  # type: ignore[method-assign]
        self.add_item(self.cashout_button)
        self.again_button: discord.ui.Button[Any] = discord.ui.Button(
            label="🎯 Дахин тоглох",
            style=discord.ButtonStyle.success,
            custom_id="minefield_again",
            row=4,
        )
        self.again_button.callback = self._on_again  # type: ignore[method-assign]
        self.add_item(self.again_button)
        self._sync()

    def _make_reveal(self, tile: int):
        async def reveal(interaction: discord.Interaction) -> None:
            state = await self.service.reveal(self.author_id, self.state.game_id, tile)
            self.state = state
            self._sync()
            await refresh_panel(
                interaction,
                embed=minefield_embed(state, self.display_name),
                view=self,
            )

        return reveal

    async def _on_cashout(self, interaction: discord.Interaction) -> None:
        state = await self.service.cashout(self.author_id, self.state.game_id)
        self.state = state
        self._sync()
        await refresh_panel(
            interaction,
            embed=minefield_embed(state, self.display_name),
            view=self,
        )

    async def _on_again(self, interaction: discord.Interaction) -> None:
        async def submit(it: discord.Interaction, value: str) -> None:
            state = await self.service.start(
                it.user.id, value, mines=self.state.mines_total
            )
            self.state = state
            self._sync()
            await refresh_panel(
                it,
                embed=minefield_embed(state, self.display_name),
                view=self,
            )

        await interaction.response.send_modal(
            BetModal(game="Minefield", callback=submit)
        )

    def _sync(self) -> None:
        for tile in range(16):
            button = self._tiles[tile]
            if tile in self.state.revealed:
                button.disabled = True
                button.label = "💎"
            elif tile in self.state.bombs:
                button.disabled = True
                button.label = "💥"
            elif not self.state.active:
                button.disabled = True
                button.label = "⬛"
            else:
                button.disabled = False
                button.label = str(tile + 1)
        self.cashout_button.disabled = not self.state.active
        self.again_button.disabled = self.state.active

    async def on_timeout(self) -> None:
        if self.state.active:
            try:
                state = await self.service.cashout(self.author_id, self.state.game_id)
                self.state = state
                self._sync()
            except Exception as exc:
                log.debug("Minefield timeout бүтэхгүй", exc_info=exc)
        await super().on_timeout()
