"""Games Boss cog — a!boss [boss_id]."""

from __future__ import annotations

from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_view
from core.exceptions import AetherError
from ui.embeds import boss_status_embed
from ui.games.boss_view import BossView


class Boss(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="boss", aliases=["wyrm", "raider"])
    async def boss(self, ctx: commands.Context, boss_id: str | None = None) -> None:
        try:
            user = await self.bot.wallet.balance(ctx.author.id)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        bosses = BossView.available_bosses()
        available = [b for b in bosses if user.level >= b.min_level]
        if boss_id:
            try:
                status = await self.bot.boss.status(boss_id)
            except AetherError as exc:
                await maybe_error(ctx, exc)
                return
        else:
            if not available:
                await maybe_error(ctx, AetherError("✦ 단 main_boss"))
                return
            status = await self.bot.boss.status(available[0].boss_id)
        boss_ids = [b.boss_id for b in available]
        view = BossView(boss_ids, self.bot.boss, ctx.author.display_name)
        if view.selected != status.boss.boss_id:
            view.selected = status.boss.boss_id
        await send_view(ctx, embed=boss_status_embed(status), view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Boss(bot))
