"""Shop view — ангилал/item StringSelect + BuyQuantityModal."""

from __future__ import annotations

from typing import Any

import discord

from repositories.shop_repo import ShopItemRow
from services.economy.wallet_service import WalletService
from services.rpg.inventory_service import InventoryService
from services.rpg.shop_service import ShopService
from ui.common.base import AetherView, refresh_panel
from ui.common.modals import BuyQuantityModal
from ui.embeds import format_number, purchase_embed, shop_embed

CATEGORIES = ("all", "defense", "booster", "title", "scroll", "tool", "consumable")


class ShopView(AetherView):
    def __init__(
        self,
        author_id: int,
        shop: ShopService,
        wallet: WalletService,
        inventory: InventoryService,
        display_name: str,
        items: list[ShopItemRow],
        category: str = "all",
    ) -> None:
        super().__init__(author_id, timeout=300.0)
        self.shop = shop
        self.wallet = wallet
        self.inventory = inventory
        self.display_name = display_name
        self.items = items
        self.category = category
        self.selected: ShopItemRow | None = None

        self.category_select: discord.ui.Select[Any] = discord.ui.Select(
            placeholder="🗂️ Ангилал",
            options=[
                discord.SelectOption(
                    label=value.title(), value=value, default=value == category
                )
                for value in CATEGORIES
            ],
            custom_id="shop_category",
        )
        self.category_select.callback = self._select_category  # type: ignore[method-assign]
        self.add_item(self.category_select)

        self.item_select: discord.ui.Select[Any] = discord.ui.Select(
            placeholder="🛒 Item сонгох...",
            options=self._item_options(),
            custom_id="shop_item",
            row=1,
        )
        self.item_select.callback = self._select_item  # type: ignore[method-assign]
        self.add_item(self.item_select)

    def _item_options(self) -> list[discord.SelectOption]:
        return [
            discord.SelectOption(
                label=f"{item.icon} {item.name} — {format_number(item.price)} ⛃"[:100],
                value=item.item_id,
                description=item.description[:100],
                default=self.selected is not None
                and item.item_id == self.selected.item_id,
            )
            for item in self.items[:25]
        ]

    async def _current_embed(self, user_id: int) -> discord.Embed:
        user = await self.wallet.balance(user_id)
        embed = shop_embed(
            self.items,
            user.wallet,
            None if self.category == "all" else self.category,
        )
        if self.selected is not None:
            embed.add_field(
                name=f"🎯 Сонгосон: {self.selected.icon} {self.selected.name}",
                value=(
                    f"`{self.selected.item_id}` · "
                    f"**{format_number(self.selected.price)}** ⛃\n"
                    f"{self.selected.description}"
                ),
                inline=False,
            )
        return embed

    async def _select_category(self, interaction: discord.Interaction) -> None:
        self.category = self.category_select.values[0]
        self.items = await self.shop.list_items(
            None if self.category == "all" else self.category
        )
        self.selected = None
        self.item_select.options = self._item_options()
        self.buy_button.disabled = True
        await refresh_panel(
            interaction,
            embed=await self._current_embed(interaction.user.id),
            view=self,
        )

    async def _select_item(self, interaction: discord.Interaction) -> None:
        item_id = self.item_select.values[0]
        self.selected = next(
            (item for item in self.items if item.item_id == item_id), None
        )
        self.buy_button.disabled = self.selected is None
        await refresh_panel(
            interaction,
            embed=await self._current_embed(interaction.user.id),
            view=self,
        )

    @discord.ui.button(
        label="💳 Худалдаж авах",
        style=discord.ButtonStyle.success,
        custom_id="shop_buy",
        row=2,
        disabled=True,
    )
    async def buy_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        item = self.selected
        if item is None:
            return
        price = await self.shop.price_for(interaction.user.id, item)

        async def submit(it: discord.Interaction, value: str) -> None:
            result = await self.shop.buy(it.user.id, item.item_id, value)
            await refresh_panel(
                it,
                embed=purchase_embed(result, self.display_name),
                view=self,
            )

        await interaction.response.send_modal(
            BuyQuantityModal(
                item_name=item.name,
                callback=submit,
                price=price,
            )
        )

    @discord.ui.button(
        label="🎒 Inventory",
        style=discord.ButtonStyle.secondary,
        custom_id="shop_inventory",
        row=2,
    )
    async def inventory_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        from ui.rpg.inventory_view import InventoryView

        embed, view = await InventoryView.create(
            interaction.user.id,
            self.inventory,
            self.display_name,
        )
        await refresh_panel(interaction, embed=embed, view=view)
