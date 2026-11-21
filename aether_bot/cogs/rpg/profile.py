"""RPG Profile cog — a!profile / a!rank / a!leaderboard."""

from __future__ import annotations

import discord
from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_embed, send_view
from core.exceptions import AetherError
from ui.embeds import (
    base_embed,
    format_number,
    profile_embed,
    progress_bar,
)
from ui.rpg.profile_view import ProfileView


class Profile(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="profile", aliases=["prof"])
    async def profile(
        self, ctx: commands.Context, member: discord.Member | None = None
    ) -> None:
        target = member or ctx.author
        try:
            user = await self.bot.wallet.balance(target.id)
            mods = await self.bot.skills.get_modifiers(target.id)
            progress = await self.bot.levels.progress(target.id)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        embed = profile_embed(user, mods, progress, target.display_name)
        if target == ctx.author:
            view = ProfileView(
                ctx.author.id,
                target.display_name,
                self.bot.user_repo,
                self.bot.wallet,
                self.bot.levels,
                self.bot.skills,
                self.bot.inventory,
            )
            await send_view(ctx, embed=embed, view=view)
        else:
            await send_embed(ctx, embed)

    @commands.command(name="rank")
    async def rank(self, ctx: commands.Context) -> None:
        user = await self.bot.wallet.balance(ctx.author.id)
        progress = await self.bot.levels.progress(ctx.author.id)
        embed = base_embed(
            f"⚡ {ctx.author.display_name} — Lv.{user.level}",
            f"{progress_bar(progress.xp, progress.required_xp)} "
            f"`{format_number(progress.xp)}/{format_number(progress.required_xp)}` XP",
        )
        embed.add_field(name="🔐 SP", value=f"**{user.skill_points}**")
        await send_embed(ctx, embed)

    @commands.command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx: commands.Context, category: str = "level") -> None:
        categories = {"level": "🏆 Level", "wealth": "💰 Wealth", "casino": "🎰 Casino"}
        title = categories.get(category, "🏆 Level")
        try:
            users = await self.bot.user_repo.leaderboard(category)
        except ValueError:
            await ctx.reply(
                "✦ Category бүртгэлгүй: level/wealth/casino", ephemeral=True
            )
            return
        embed = base_embed(f"{title} — Aether Leaderboard", color=0x2ECC71)
        if not users:
            embed.add_field(name="Хэлүүд үнэгүй", value="Тоглогчид орсонгүй.")
        for index, row in enumerate(users[:10], start=1):
            value = (
                f"Lv.{row.level} · `{format_number(row.wallet)}` ⛃"
                if category == "wealth"
                else f"Lv.{row.level} · XP {format_number(row.xp)}"
            )
            if category == "casino":
                value = f"🎰 {format_number(row.casino_net)} ⛃"
            embed.add_field(
                name=f"{index}. <@{row.user_id}>",
                value=value,
                inline=True,
            )
        await send_embed(ctx, embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Profile(bot))
