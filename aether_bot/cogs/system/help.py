"""System cog — a!help, a!ping, a!settings (зөвхөн prefix)."""

from __future__ import annotations

from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import send_embed, send_view
from ui.embeds import base_embed
from ui.system.help_view import (
    CATEGORY_TITLES,
    HelpView,
    help_embed,
)


class System(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="help", aliases=["h"])
    async def help(self, ctx: commands.Context, category: str = "economy") -> None:
        key = category.lower()
        if key not in CATEGORY_TITLES:
            key = "economy"
        embed = help_embed(key)
        view = HelpView(ctx.author.id, category=key)
        await send_view(ctx, embed=embed, view=view)

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context) -> None:
        latency = int(self.bot.latency * 1000) if self.bot.latency else 0
        embed = base_embed(
            "⏱️ Aether Ping",
            f"Нүр бийрт `{latency}` ms",
            color=0x2ECC71,
        )
        await send_embed(ctx, embed)

    @commands.command(name="settings")
    async def settings(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            await ctx.reply("✦ Энэ команд сервер дээр ажиллана.", ephemeral=True)
            return
        settings = await self.bot.guild_repo.get_or_create(ctx.guild.id)
        channel = self.bot.get_channel(settings.log_channel_id)
        channel_name = channel.name if channel else "— Тохирохгүй"
        embed = base_embed(
            "⚙️ Aether Settings",
            "Guild тохиргоо: prefix, tax, лог канал.",
            color=0x5865F2,
        )
        embed.add_field(name="🧩 Prefix", value=f"`{settings.prefix}`", inline=True)
        embed.add_field(
            name="🧾 Tax", value=f"**{settings.tax_pct * 100:.1f}%**", inline=True
        )
        embed.add_field(name="🪪 Log channel", value=f"#{channel_name}", inline=False)
        embed.set_footer(text="✦ Aether System • a!admin_config log_channel")
        await send_embed(ctx, embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(System(bot))
