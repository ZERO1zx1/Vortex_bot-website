"""Casino Crash cog — a!crash / a!crash <бооцоо>."""

from __future__ import annotations

from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from cogs._helpers import maybe_error, send_view
from core.exceptions import AetherError
from ui.casino.crash_view import CrashView
from ui.embeds import crash_embed, start_casino_embed


class Crash(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @commands.command(name="crash", aliases=["cr"])
    async def crash(self, ctx: commands.Context, bet: str | None = None) -> None:
        if bet is not None:
            try:
                state = await self.bot.crash.start(ctx.author.id, bet)
            except AetherError as exc:
                await maybe_error(ctx, exc)
                return
            view = CrashView(
                ctx.author.id,
                self.bot.crash,
                ctx.author.display_name,
                state=state,
            )
            await send_view(
                ctx,
                embed=crash_embed(state, ctx.author.display_name),
                view=view,
            )
            return
        view = CrashView(ctx.author.id, self.bot.crash, ctx.author.display_name)
        await send_view(
            ctx,
            embed=start_casino_embed("crash", ctx.author.display_name),
            view=view,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Crash(bot))
