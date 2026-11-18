"""Серверийн тохиргооны админ командууд."""

from __future__ import annotations

import discord
from discord.ext import commands

from cogs._helpers import reply_error
from config import DEFAULT_PREFIX


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="setprefix",
        description="Серверийн prefix-ийг өөрчилнө (1–5 тэмдэгт).",
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def setprefix(self, ctx: commands.Context, prefix: str) -> None:
        prefix = prefix.strip()
        if not 1 <= len(prefix) <= 5 or any(ch.isspace() for ch in prefix):
            await reply_error(ctx, "✦ Prefix нь зайгүй, 1–5 тэмдэгт байх ёстой.")
            return
        assert ctx.guild is not None
        await self.bot.db.execute(  # type: ignore[attr-defined]
            """
            INSERT INTO guild_settings (guild_id, prefix)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                prefix = excluded.prefix,
                updated_at = datetime('now')
            """,
            (ctx.guild.id, prefix),
        )
        embed = discord.Embed(
            title="⚙️ Серверийн тохиргоо",
            description=f"Prefix **`{prefix}`** болж өөрчлөгдлөө.",
            color=0x2ECC71,
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(
        name="settings",
        description="Серверийн одоогийн тохиргоог харуулна.",
    )
    @commands.guild_only()
    async def settings(self, ctx: commands.Context) -> None:
        assert ctx.guild is not None
        row = await self.bot.db.fetchone(  # type: ignore[attr-defined]
            "SELECT prefix, tax_pct FROM guild_settings WHERE guild_id = ?",
            (ctx.guild.id,),
        )
        prefix = row["prefix"] if row else DEFAULT_PREFIX
        tax = row["tax_pct"] if row else 0.0
        embed = discord.Embed(
            title="⚙️ Серверийн тохиргоо",
            color=0x5865F2,
        )
        embed.add_field(name="Prefix", value=f"`{prefix}`", inline=True)
        embed.add_field(name="Tax", value=f"{tax * 100:.1f}%", inline=True)
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
