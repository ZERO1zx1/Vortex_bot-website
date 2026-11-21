"""Slots view — Бооцогоо тавих товч + refresh товчон даахуй."""

from __future__ import annotations

from typing import Any

import discord

from services.casino.slots_service import SlotsService
from ui.common.base import AetherView, refresh_panel
from ui.common.modals import BetModal
from ui.common.paginator import Paginator
from ui.embeds import slots_embed


class SlotsView(AetherView):
    def __init__(
        self,
        author_id: int,
        service: SlotsService,
        display_name: str,
    ) -> None:
        super().__init__(author_id)
        self.service = service
        self.display_name = display_name

    @discord.ui.button(
        label="🎰 Бооцогоо тавих",
        style=discord.ButtonStyle.success,
        custom_id="slots_bet_again",
    )
    async def spin_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        async def submit(it: discord.Interaction, value: str) -> None:
            result = await self.service.spin(it.user.id, value)
            await refresh_panel(
                it,
                embed=slots_embed(result, self.display_name),
                view=self,
            )

        await interaction.response.send_modal(BetModal(game="Slots", callback=submit))

    @discord.ui.button(
        label="📜 casino_logs — Түүх",
        style=discord.ButtonStyle.secondary,
        custom_id="slots_history",
    )
    async def history_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        history = await self.service.logs.recent_casino(interaction.user.id)
        from ui.embeds import base_embed

        pages = [
            _history_page(chunk, self.display_name) for chunk in _chunks(history, 5)
        ] or [
            base_embed(
                "📜 casino_logs — Түүх",
                "Жараар оюун ашгийн бүртгэл бүтэлгүйтлээ.",
                color=0x5865F2,
            )
        ]
        paginator = Paginator(interaction.user.id, pages, timeout=120.0)
        await refresh_panel(interaction, embed=paginator.page, view=paginator)


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _history_page(rows: list[Any], display_name: str) -> discord.Embed:
    from ui.embeds import base_embed, format_number

    embed = base_embed(
        f"📜 casino_logs — {display_name}",
        "`a!slots <бооцоо>`-оор дахин ажиллуулна уу.",
        color=0x5865F2,
    )
    for row in rows:
        embed.add_field(
            name=f"🎮 {row.game.upper()} — {row.outcome}",
            value=(
                f"Бооцоо **{format_number(row.bet)}** · Төлбөр "
                f"**{format_number(row.payout)}** · Net "
                f"**{row.net:+}** · `{row.created_at[11:16]}`"
            ),
            inline=False,
        )
    return embed
