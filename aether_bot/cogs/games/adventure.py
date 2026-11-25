"""Games Adventure cog — a!adventure [dungeon]."""

from __future__ import annotations

from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_embed, send_view
from core.checks import not_jailed
from core.exceptions import AetherError, DungeonNotFoundError
from ui.embeds import adventure_embed, base_embed
from ui.games.adventure_view import AdventureView


class Adventure(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="adventure", aliases=["adv"])
    @not_jailed()
    async def adventure(
        self, ctx: commands.Context, dungeon: str | None = None
    ) -> None:
        user = await self.bot.wallet.balance(ctx.author.id)
        if dungeon:
            try:
                result = await self.bot.adventure.explore(ctx.author.id, dungeon)
            except AetherError as exc:
                await maybe_error(ctx, exc)
                return
            await send_embed(ctx, adventure_embed(result, ctx.author.display_name))
            return
        try:
            dungeons = self.bot.adventure.dungeons_for(user.level)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        if not dungeons:
            await maybe_error(ctx, DungeonNotFoundError())
            return
        view = AdventureView(
            ctx.author.id, self.bot.adventure, dungeons, ctx.author.display_name
        )
        embed = base_embed(
            "🗺️ dungeon сонгох",
            "Доорхыг сонгох: амжилттай бол олз авна.",
            color=0x8A2BE2,
        )
        await send_view(ctx, embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Adventure(bot))
