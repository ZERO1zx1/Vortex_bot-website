"""Skill tree командууд."""

from __future__ import annotations

from discord.ext import commands

from cogs._helpers import reply_error
from core.exceptions import AetherError
from core.skill_catalog import SKILLS
from ui.embeds import base_embed, skills_embed


class Skills(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="skills",
        description="Skill tree, SP болон cooldown-уудыг харуулна.",
    )
    async def skills(self, ctx: commands.Context) -> None:
        try:
            tree = await self.bot.skills.get_tree(ctx.author.id)  # type: ignore[attr-defined]
        except AetherError as exc:
            await reply_error(ctx, exc.user_message)
            return
        await ctx.reply(embed=skills_embed(tree), mention_author=False)

    @commands.hybrid_command(
        name="upgrade",
        description="1 SP зарцуулж skill-ийн түвшинг нэмнэ.",
    )
    async def upgrade(self, ctx: commands.Context, skill_id: str) -> None:
        skill = SKILLS.get(skill_id.strip().lower())
        if skill is None:
            await reply_error(ctx, self._unknown_skill_message())
            return
        try:
            result = await self.bot.skills.upgrade(ctx.author.id, skill.skill_id)  # type: ignore[attr-defined]
        except AetherError as exc:
            await reply_error(ctx, exc.user_message)
            return
        embed = base_embed(
            f"{result.skill.icon} {result.skill.name} — Lv.{result.new_level}",
            f"Skill амжилттай сайжирлаа. Үлдсэн SP: **{result.skill_points_left}**.",
            color=0x2ECC71,
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(
        name="activate",
        description="Active skill-ийг идэвхжүүлнэ.",
    )
    async def activate(self, ctx: commands.Context, skill_id: str) -> None:
        skill = SKILLS.get(skill_id.strip().lower())
        if skill is None:
            await reply_error(ctx, self._unknown_skill_message())
            return
        try:
            result = await self.bot.skills.activate(ctx.author.id, skill.skill_id)  # type: ignore[attr-defined]
        except AetherError as exc:
            await reply_error(ctx, exc.user_message)
            return
        embed = base_embed(
            f"{result.skill.icon} {result.skill.name} — Идэвхтэй",
            f"Дуусах: <t:{int(result.active_until.timestamp())}:R>\n"
            f"Cooldown: **{result.cooldown_sec // 60} минут**.",
            color=0x00E5FF,
        )
        await ctx.reply(embed=embed, mention_author=False)

    @staticmethod
    def _unknown_skill_message() -> str:
        valid = ", ".join(f"`{skill_id}`" for skill_id in SKILLS)
        return f"✦ Ийм skill байхгүй. Боломжтой ID: {valid}"


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Skills(bot))
