"""Энгийн хуудаслагч View — embed жагсаалтыг Previous/Next-ээр эргэлдүүлнэ."""

from __future__ import annotations

from typing import Any

import discord

from ui.common.base import AetherView


class Paginator(AetherView):
    def __init__(
        self,
        author_id: int,
        pages: list[discord.Embed],
        *,
        timeout: float = 180.0,
    ) -> None:
        super().__init__(author_id, timeout=timeout)
        if not pages:
            raise ValueError("pages хоосон байж болохгүй")
        self.pages = pages
        self.index = 0
        self._sync()

    @property
    def page(self) -> discord.Embed:
        return self.pages[self.index]

    def _sync(self) -> None:
        self.previous.disabled = self.index <= 0
        self.next.disabled = self.index >= len(self.pages) - 1
        self.counter.label = f"{self.index + 1}/{len(self.pages)}"

    async def _show(self, interaction: discord.Interaction, index: int) -> None:
        self.index = max(0, min(index, len(self.pages) - 1))
        self._sync()
        await interaction.response.edit_message(embed=self.page, view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self._show(interaction, self.index - 1)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def counter(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:  # pragma: no cover — disabled
        await interaction.response.defer()

    @discord.ui.button(label="▶", style=discord.ButtonStyle.primary)
    async def next(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self._show(interaction, self.index + 1)

    @discord.ui.button(label="✖ Хаах", style=discord.ButtonStyle.danger, row=1)
    async def close(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        await interaction.response.edit_message(view=self)
        self.stop()
