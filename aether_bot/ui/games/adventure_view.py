"""Adventure view — dungeon StringSelect → explore."""

from __future__ import annotations

from typing import Any

import discord

from core.exceptions import AetherError
from services.games.adventure_service import AdventureService, DungeonDef
from ui.common.base import AetherView, refresh_panel, respond_error
from ui.embeds import adventure_embed


class AdventureView(AetherView):
    def __init__(
        self,
        author_id: int,
        service: AdventureService,
        dungeons: list[DungeonDef],
        display_name: str,
    ) -> None:
        super().__init__(author_id, timeout=300.0)
        self.service = service
        self.display_name = display_name
        self.select: discord.ui.Select[Any] = discord.ui.Select(
            placeholder="🗺️ Dungeon сонгох...",
            options=[
                discord.SelectOption(
                    label=f"{dungeon.icon} {dungeon.name}",
                    value=dungeon.dungeon_id,
                    description=dungeon.description[:100],
                )
                for dungeon in dungeons[:25]
            ],
            custom_id="adventure_select",
        )
        self.select.callback = self._select  # type: ignore[method-assign]
        self.add_item(self.select)

    async def _select(self, interaction: discord.Interaction) -> None:
        try:
            result = await self.service.explore(
                interaction.user.id, self.select.values[0]
            )
        except AetherError as exc:
            await respond_error(interaction, exc)
            return
        self.select.disabled = True
        await refresh_panel(
            interaction,
            embed=adventure_embed(result, self.display_name),
            view=self,
        )

    @discord.ui.button(
        label="🗺️ Dungeon схема",
        style=discord.ButtonStyle.secondary,
        custom_id="adventure_info",
        row=1,
    )
    async def info_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        user = await self.service.users.get_or_create(interaction.user.id)
        lines = "\n".join(
            f"{d.icon} **{d.name}** — {d.description} · Lv.{d.min_level}"
            for d in self.service.dungeons_for(user.level)
        )
        embed = _info_embed(user.level, lines or "Dungeon байхгүй.")
        await refresh_panel(interaction, embed=embed, view=self)


def _info_embed(level: int, lines: str) -> discord.Embed:
    from ui.embeds import base_embed

    embed = base_embed(
        f"🗺️ dungeon схема — Lv.{level}",
        lines,
        color=0x8A2BE2,
    )
    return embed
