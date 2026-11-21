"""Jail view — Батлан даалтаар гарах товч."""

from __future__ import annotations

from typing import Any

import discord

import config
from services.economy.jail_service import JailService, JailStatus
from ui.common.base import AetherView, refresh_panel
from ui.embeds import base_embed, format_number, jail_embed


class JailView(AetherView):
    def __init__(
        self,
        author_id: int,
        jail: JailService,
        status: JailStatus,
        display_name: str,
    ) -> None:
        super().__init__(author_id)
        self.jail = jail
        self.status = status
        self.display_name = display_name
        self.bail_button.disabled = not status.jailed

    @discord.ui.button(
        label="💰 Батлан даалтаар гарах",
        style=discord.ButtonStyle.success,
        custom_id="jail_bail",
    )
    async def bail_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        cost = self.status.bail_cost
        await self.jail.bail(interaction.user.id)
        self.status = await self.jail.status(interaction.user.id)
        self.bail_button.disabled = True
        embed = base_embed(
            "🕊️ Aether Шорон — Чөлөөлөгдлөө",
            "Та батлан даалтаа төлж, сүүдрийн хязгаараас гарлаа.",
            color=config.SUCCESS,
        )
        embed.add_field(
            name="💸 Төлсөн",
            value=f"**{format_number(cost)}** ⛃",
        )
        await refresh_panel(interaction, embed=embed, view=self)

    @discord.ui.button(
        label="📜 Төлөв",
        style=discord.ButtonStyle.secondary,
        custom_id="jail_status",
    )
    async def refresh_status(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        self.status = await self.jail.status(interaction.user.id)
        self.bail_button.disabled = not self.status.jailed
        await refresh_panel(
            interaction,
            embed=jail_embed(self.status, self.display_name),
            view=self,
        )
