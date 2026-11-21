"""Economy Crime cog — a!crime / a!rob / a!jail / a!bail."""

from __future__ import annotations

import discord
from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_embed
from core.checks import not_jailed
from core.exceptions import AetherError
from ui.economy.crime_view import CrimeView
from ui.economy.jail_view import JailView
from ui.embeds import crime_embed, rob_embed


class Crime(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="crime", aliases=["c"])
    @not_jailed()
    async def crime(self, ctx: commands.Context, crime_id: str | None = None) -> None:
        if crime_id:
            try:
                result = await self.bot.crime.crime(ctx.author.id, crime_id)
            except AetherError as exc:
                await maybe_error(ctx, exc)
                return
            await send_embed(ctx, crime_embed(result, ctx.author.display_name))
            return
        user = await self.bot.wallet.balance(ctx.author.id)
        crimes = self.bot.crime.crimes_for(user.level)
        if not crimes:
            try:
                await self.bot.crime.crime(ctx.author.id, "default_set")
            except AetherError as exc:
                await maybe_error(ctx, exc)
                return
        view = CrimeView(ctx.author.id, self.bot.crime, crimes, ctx.author.display_name)
        embed = _select_embed(crimes)
        message = await ctx.reply(embed=embed, view=view, mention_author=False)
        view.message = message

    @commands.command(name="rob", aliases=["r"])
    @not_jailed()
    async def rob(self, ctx: commands.Context, target: discord.Member) -> None:
        try:
            result = await self.bot.crime.rob(ctx.author.id, target.id)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        actor = ctx.author.display_name
        await send_embed(ctx, rob_embed(result, actor, target.display_name))

    @commands.command(name="jail")
    async def jail(self, ctx: commands.Context) -> None:
        status = await self.bot.jail.status(ctx.author.id)
        view = JailView(ctx.author.id, self.bot.jail, status, ctx.author.display_name)
        from ui.embeds import jail_embed

        message = await ctx.reply(
            embed=jail_embed(status, ctx.author.display_name), view=view
        )
        view.message = message

    @commands.command(name="bail")
    async def bail(self, ctx: commands.Context) -> None:
        try:
            result = await self.bot.jail.bail(ctx.author.id)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        await send_embed(ctx, _bail_embed(result))


def _select_embed(crimes) -> discord.Embed:
    from ui.embeds import base_embed, format_number

    embed = base_embed(
        "🕶️ Aether Crime — Сонгох",
        "Гэмт хэрэг сонгохгүй бол урилга харж байна.",
    )
    for crime in crimes[:20]:
        embed.add_field(
            name=f"{crime.icon} {crime.name} — `{crime.crime_id}`",
            value=(
                f"Амжилт **{crime.success_chance * 100:.0f}%** · "
                f"Олз {format_number(crime.min_reward)}–"
                f"{format_number(crime.max_reward)} ⛃ · "
                f"Шорон {crime.jail_minutes}м"
            ),
            inline=False,
        )
    return embed


def _bail_embed(result) -> discord.Embed:
    from ui.embeds import base_embed

    return base_embed(
        "🕊️ Aether Шорон — Чөлөөлөгдлөө",
        f"Батлан даалтаар гарлаа. Төлсөн **{result.bail_cost:,}** ⛃.",
        color=0x2ECC71,
    )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Crime(bot))
