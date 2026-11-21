"""Lottery view — тасалбар авах Buy + Jackpot Draw."""

from __future__ import annotations

from typing import Any

import discord

from services.casino.lottery_service import LotteryService
from ui.common.base import AetherView, refresh_panel
from ui.common.modals import BuyQuantityModal
from ui.embeds import lottery_embed


class LotteryView(AetherView):
    def __init__(
        self,
        author_id: int,
        service: LotteryService,
        display_name: str,
    ) -> None:
        super().__init__(author_id, timeout=600.0)
        self.service = service
        self.display_name = display_name

    async def _info_embed(self) -> discord.Embed:
        info = await self.service.info()
        return lottery_embed(info, self.display_name)

    async def _update_panel(self, interaction: discord.Interaction) -> None:
        await refresh_panel(interaction, embed=await self._info_embed(), view=self)

    @discord.ui.button(
        label="🎟️ Тасалбар авах",
        style=discord.ButtonStyle.success,
        custom_id="lottery_buy",
    )
    async def buy_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        info = await self.service.info()
        bought = await self.service.my_tickets(interaction.user.id)
        remaining = max(1, info.max_per_user - bought)
        price = info.price

        async def submit(it: discord.Interaction, value: str) -> None:
            await self.service.buy(it.user.id, value)
            await self._update_panel(it)

        await interaction.response.send_modal(
            BuyQuantityModal(
                item_name="Тасалбар",
                callback=submit,
                price=price * max(1, remaining),
            )
        )

    @discord.ui.button(
        label="🎉 Дүртээс сугалах",
        style=discord.ButtonStyle.primary,
        custom_id="lottery_draw",
    )
    async def draw_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self.service.draw()
        await self._update_panel(interaction)

    @discord.ui.button(
        label="📜 Статистик",
        style=discord.ButtonStyle.secondary,
        custom_id="lottery_info",
        row=1,
    )
    async def info_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await refresh_panel(interaction, embed=await self._info_embed(), view=self)
