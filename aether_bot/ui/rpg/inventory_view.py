"""Inventory view — StringSelect item + Use button."""

from __future__ import annotations

from typing import Any

import discord

from repositories.shop_repo import InventoryRow
from services.rpg.inventory_service import InventoryService
from ui.common.base import AetherView, refresh_panel
from ui.embeds import base_embed, inventory_embed, use_item_embed


class InventoryView(AetherView):
    def __init__(
        self,
        author_id: int,
        inventory: InventoryService,
        display_name: str,
        rows: list[InventoryRow],
        effects: list[Any] | None = None,
    ) -> None:
        super().__init__(author_id, timeout=600.0)
        self.inventory = inventory
        self.display_name = display_name
        self.rows = rows
        self.selected: str | None = None

        self.item_select: discord.ui.Select[Any] = discord.ui.Select(
            placeholder="🧰 Item сонгох...",
            options=self._item_options(),
            custom_id="inventory_select",
        )
        self.item_select.callback = self._select_item  # type: ignore[method-assign]
        self.add_item(self.item_select)
        self.use_button.disabled = True

    @classmethod
    async def create(
        cls,
        author_id: int,
        inventory: InventoryService,
        display_name: str,
    ) -> tuple[discord.Embed, InventoryView]:
        rows = await inventory.inventory(author_id)
        effects = await inventory.active_effects(author_id)
        return inventory_embed(rows, effects, display_name), cls(
            author_id, inventory, display_name, rows, effects
        )

    def _item_options(self) -> list[discord.SelectOption]:
        options = []
        for row in self.rows[:25]:
            item = row.item
            options.append(
                discord.SelectOption(
                    label=f"{item.icon} {item.name} ×{row.quantity}"[:100],
                    value=item.item_id,
                    description=item.description[:100],
                )
            )
        return options

    async def _update_panel(self, interaction: discord.Interaction) -> None:
        self.rows = await self.inventory.inventory(interaction.user.id)
        self.item_select.options = self._item_options()
        self.selected = None
        self.use_button.disabled = True
        embed = inventory_embed(self.rows, [], self.display_name)
        await refresh_panel(interaction, embed=embed, view=self)

    async def _select_item(self, interaction: discord.Interaction) -> None:
        self.selected = self.item_select.values[0]
        self.use_button.disabled = False
        await refresh_panel(
            interaction,
            embed=base_embed(
                "🎒 Aether Inventory",
                f"Сонгосон: **{self.selected}** — `{next(r.item.name for r in self.rows if r.item.item_id == self.selected)}`",
                color=0x2ECC71,
            ),
            view=self,
        )

    @discord.ui.button(
        label="✨ Ашиглах",
        style=discord.ButtonStyle.success,
        custom_id="inventory_use",
        row=1,
        disabled=True,
    )
    async def use_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        if self.selected is None:
            return
        result = await self.inventory.use(interaction.user.id, self.selected)
        await refresh_panel(
            interaction,
            embed=use_item_embed(result, self.display_name),
            view=self,
        )
        self.selected = None
        self.use_button.disabled = True
        self.rows = await self.inventory.inventory(interaction.user.id)
        self.item_select.options = self._item_options()
