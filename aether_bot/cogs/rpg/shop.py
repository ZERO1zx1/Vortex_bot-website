"""RPG Shop cog — a!shop / a!buy / a!equip (зөвхөн prefix)."""

from __future__ import annotations

from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_embed, send_view
from core.exceptions import AetherError
from ui.embeds import base_embed, purchase_embed, shop_embed
from ui.rpg.shop_view import ShopView


class Shop(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="shop", aliases=["st"])
    async def shop(self, ctx: commands.Context, category: str | None = None) -> None:
        try:
            items = await self.bot.shop.list_items(category)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        user = await self.bot.wallet.balance(ctx.author.id)
        view = ShopView(
            ctx.author.id,
            self.bot.shop,
            self.bot.wallet,
            self.bot.inventory,
            ctx.author.display_name,
            items,
            category="all" if category is None else category,
        )
        embed = shop_embed(items, user.wallet, category)
        await send_view(ctx, embed=embed, view=view)

    @commands.command(name="buy")
    async def buy(self, ctx: commands.Context, item_id: str, quantity: int = 1) -> None:
        try:
            result = await self.bot.shop.buy(ctx.author.id, item_id, quantity)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        await send_embed(ctx, purchase_embed(result, ctx.author.display_name))

    @commands.command(name="equip")
    async def equip(self, ctx: commands.Context, item_id: str) -> None:
        try:
            title = await self.bot.shop.equip_title(ctx.author.id, item_id)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        embed = base_embed(
            f"👑 {title}",
            "Энэ Title эзэнтэй дээрээ зүүсэн байна.",
            color=0xFFD700,
        )
        await send_embed(ctx, embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Shop(bot))
