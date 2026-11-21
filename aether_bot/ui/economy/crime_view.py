"""Crime view — гэмт хэргийг StringSelect-ээр сонгоно."""

from __future__ import annotations

from typing import Any

import discord

import config
from services.economy.crime_service import CrimeDef, CrimeService
from ui.common.base import AetherView, refresh_panel
from ui.embeds import base_embed, crime_embed, format_number


class CrimeView(AetherView):
    def __init__(
        self,
        author_id: int,
        crime_service: CrimeService,
        crimes: list[CrimeDef],
        display_name: str,
    ) -> None:
        super().__init__(author_id)
        self.crime_service = crime_service
        self.display_name = display_name
        self.crimes = crimes
        options = [
            discord.SelectOption(
                label=f"{crime.icon} {crime.name}"[:100],
                value=crime.crime_id,
                description=(
                    f"Амжилт {crime.success_chance * 100:.0f}% · "
                    f"{format_number(crime.min_reward)}–{format_number(crime.max_reward)} ⛃"
                )[:100],
            )
            for crime in crimes[:25]
        ]
        self.crime_select: discord.ui.Select[Any] = discord.ui.Select(
            placeholder="🕶️ Гэмт хэрэг сонгох...",
            options=options,
            custom_id="crime_select",
        )
        self.crime_select.callback = self._select_crime  # type: ignore[method-assign]
        self.add_item(self.crime_select)

    async def _select_crime(self, interaction: discord.Interaction) -> None:
        result = await self.crime_service.crime(
            interaction.user.id, self.crime_select.values[0]
        )
        self.crime_select.disabled = True
        await refresh_panel(
            interaction,
            embed=crime_embed(result, self.display_name),
            view=self,
        )

    @discord.ui.button(
        label="📜 Дүрэм",
        style=discord.ButtonStyle.secondary,
        custom_id="crime_rules",
        row=1,
    )
    async def rules(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        embed = base_embed(
            "🕶️ Aether Crime",
            "Амжилтгүй бол торгууль төлж, шоронд хоригдоно. "
            "Shadow Step нь эрсдэлийг бууруулна.",
            color=config.DANGER,
        )
        for crime in self.crimes:
            embed.add_field(
                name=f"{crime.icon} {crime.name} · `{crime.crime_id}`",
                value=(
                    f"Амжилт **{crime.success_chance * 100:.0f}%** · "
                    f"Олз {format_number(crime.min_reward)}–"
                    f"{format_number(crime.max_reward)} ⛃ · "
                    f"Шорон {crime.jail_minutes}м"
                ),
                inline=False,
            )
        await refresh_panel(interaction, embed=embed, view=self)
