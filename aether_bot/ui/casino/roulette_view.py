"""Roulette view — товчнуудаар сонгосон төрлөөр эргүүлнэ."""

from __future__ import annotations

from typing import Any

import discord

from core.exceptions import ValidationError
from services.casino.roulette_service import RouletteService
from ui.common.base import AetherView, refresh_panel, respond_error
from ui.common.modals import BetModal
from ui.embeds import base_embed, roulette_embed


class RouletteView(AetherView):
    def __init__(
        self,
        author_id: int,
        service: RouletteService,
        display_name: str,
    ) -> None:
        super().__init__(author_id, timeout=300.0)
        self.service = service
        self.display_name = display_name
        self.selected = "red"
        self._sync()

    def _selected_note(self) -> discord.Embed:
        return base_embed(
            "🎡 Aether Roulette",
            f"Сонгосон: **{self.selected}**\nОдоор эргүүлнэ үү.",
            color=0xFF4757,
        )

    def _sync(self) -> None:
        self.red_button.style = (
            discord.ButtonStyle.primary
            if self.selected == "red"
            else discord.ButtonStyle.secondary
        )
        self.black_button.style = (
            discord.ButtonStyle.primary
            if self.selected == "black"
            else discord.ButtonStyle.secondary
        )
        self.even_button.style = (
            discord.ButtonStyle.primary
            if self.selected == "even"
            else discord.ButtonStyle.secondary
        )
        self.odd_button.style = (
            discord.ButtonStyle.primary
            if self.selected == "odd"
            else discord.ButtonStyle.secondary
        )

    async def _select(self, interaction: discord.Interaction, value: str) -> None:
        self.selected = value
        self._sync()
        await refresh_panel(interaction, embed=self._selected_note(), view=self)

    async def _spin(self, interaction: discord.Interaction, value: str) -> None:
        result = await self.service.play(interaction.user.id, value, self.selected)
        await refresh_panel(
            interaction,
            embed=roulette_embed(result, self.display_name),
            view=self,
        )

    async def _play_number(self, interaction: discord.Interaction, value: str) -> None:
        try:
            number = int(value.strip())
        except ValueError:
            await respond_error(
                interaction,
                ValidationError("✦ Тооны тэмдэг бүрийг үнэлж болохгүй."),
            )
            return
        result = await self.service.play(
            interaction.user.id, value, "number", number=number
        )
        await refresh_panel(
            interaction,
            embed=roulette_embed(result, self.display_name),
            view=self,
        )

    @discord.ui.button(
        label="🔴 Улаан",
        style=discord.ButtonStyle.primary,
        custom_id="roulette_red",
    )
    async def red_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self._select(interaction, "red")

    @discord.ui.button(
        label="⚫ Хар",
        style=discord.ButtonStyle.primary,
        custom_id="roulette_black",
    )
    async def black_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self._select(interaction, "black")

    @discord.ui.button(
        label="➡️ Тэгш",
        style=discord.ButtonStyle.primary,
        custom_id="roulette_even",
    )
    async def even_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self._select(interaction, "even")

    @discord.ui.button(
        label="⬅️ Сонгой",
        style=discord.ButtonStyle.primary,
        custom_id="roulette_odd",
    )
    async def odd_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self._select(interaction, "odd")

    @discord.ui.button(
        label="🎡 Эргүүлэх",
        style=discord.ButtonStyle.success,
        custom_id="roulette_spin",
        row=1,
    )
    async def spin_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        async def submit(it: discord.Interaction, value: str) -> None:
            await self._spin(it, value)

        await interaction.response.send_modal(
            BetModal(game="Roulette", callback=submit)
        )

    @discord.ui.button(
        label="🔢 Тоо (0–36)",
        style=discord.ButtonStyle.secondary,
        custom_id="roulette_number",
        row=1,
    )
    async def number_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        async def submit(it: discord.Interaction, value: str) -> None:
            await self._play_number(it, value)

        await interaction.response.send_modal(
            BetModal(game="Roulette", callback=submit)
        )
