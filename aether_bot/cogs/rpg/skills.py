"""RPG Skills cog — a!skills / a!upgrade / a!activate (зөвхөн prefix)."""

from __future__ import annotations

from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_view
from core.exceptions import AetherError
from ui.embeds import base_embed, skills_embed
from ui.rpg.skill_view import SkillTreeView


class Skills(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="skills", aliases=["sk"])
    async def skills(self, ctx: commands.Context) -> None:
        try:
            tree = await self.bot.skills.get_tree(ctx.author.id)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        view = SkillTreeView(ctx.author.id, tree, self.bot.skills)
        await send_view(ctx, embed=skills_embed(tree), view=view)

    @commands.command(name="upgrade")
    async def upgrade(self, ctx: commands.Context, skill_id: str) -> None:
        try:
            result = await self.bot.skills.upgrade(ctx.author.id, skill_id)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        embed = base_embed(
            f"✅ {result.skill.name} Сайжруулаллаа",
            f"Lv.{result.previous_level} → **Lv.{result.new_level}** · "
            f"{result.skill_points_left} SP үлдсэн.",
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="activate")
    async def activate(self, ctx: commands.Context, skill_id: str) -> None:
        try:
            result = await self.bot.skills.activate(ctx.author.id, skill_id)
        except AetherError as exc:
            await maybe_error(ctx, exc)
            return
        embed = base_embed(
            f"✨ {result.skill.icon} {result.skill.name}",
            f"Идэвхтэй · <t:{int(result.active_until.timestamp())}:R> хүртэл\n"
            f"Cooldown: `{result.cooldown_sec // 60}м`",
        )
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Skills(bot))
