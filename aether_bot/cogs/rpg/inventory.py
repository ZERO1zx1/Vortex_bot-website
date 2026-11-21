"""RPG Inventory cog — a!inventory / a!use (зөвхөн prefix)."""

from __future__ import annotations

from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_embed, send_view
from core.exceptions import AetherError
from ui.embeds import use_item_embed
from ui.rpg.inventory_view import InventoryView


class Inventory(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="inventory", aliases=["inv"])
    async def inventory(self, ctx: commands.Context) -> None:
        try:
            embed, view = await InventoryView.create(
                ctx.author.id, self.bot.inventory, ctx.author.display_name
            )
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        await send_view(ctx, embed=embed, view=view)

    @commands.command(name="use")
    async def use(self, ctx: commands.Context, item_id: str) -> None:
        try:
            result = await self.bot.inventory.use(ctx.author.id, item_id)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        await send_embed(ctx, use_item_embed(result, ctx.author.display_name))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Inventory(bot))
