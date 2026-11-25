"""Economy Income cog — a!daily, a!work (зөвхөн prefix)."""

from __future__ import annotations

from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_embed, send_view
from core.checks import not_jailed
from core.exceptions import AetherError
from ui.economy.work_view import WorkView
from ui.embeds import base_embed, daily_embed


class Income(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="daily")
    async def daily(self, ctx: commands.Context) -> None:
        try:
            result = await self.bot.income.daily(ctx.author.id)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        await send_embed(ctx, daily_embed(result, ctx.author.display_name))

    @commands.command(name="work", aliases=["w"])
    @not_jailed()
    async def work(self, ctx: commands.Context, job: str | None = None) -> None:
        try:
            if job:
                result = await self.bot.income.work(ctx.author.id, job)
                from ui.embeds import work_embed

                await send_embed(ctx, work_embed(result, ctx.author.display_name))
                return
            user = await self.bot.wallet.balance(ctx.author.id)
            jobs = self.bot.income.jobs_for(user.level)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        if not jobs:
            await self.bot.income.work(ctx.author.id)  # JobNotFoundError шиднэ
            return
        view = WorkView(ctx.author.id, self.bot.income, jobs, ctx.author.display_name)
        embed = base_embed(
            "💼 Aether Jobs",
            "`a!work` — санамсаргүй, эсвэл сонгосон ажил",
        )
        await send_view(ctx, embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Income(bot))
