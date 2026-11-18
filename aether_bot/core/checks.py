"""Discord command checks: jail guard болон admin эрх.

`cogs/` давхарга зөвхөн эдгээр decorator-ийг ашиглана. Шоронгийн төлөвийг
`GuildRepository` биш `UserRepository`-оос уншина — jail нь хэрэглэгчийн
төлөв, guild-ийн биш.
"""

from __future__ import annotations

from typing import Any

from discord import app_commands
from discord.ext import commands

from core.exceptions import JailedError
from utils.time_utils import from_db, seconds_until, utcnow


async def check_not_jailed(ctx: commands.Context[Any]) -> bool:
    """Хэрэглэгч шоронд байвал `JailedError` шиднэ.

    `ctx.bot.user_repo` байхгүй (жишээ нь тест) бол чөлөөтэй гэж үзнэ.
    """
    repo = getattr(ctx.bot, "user_repo", None)
    if repo is None:
        return True
    user = await repo.get(ctx.author.id)
    until = from_db(user.jail_until) if user else None
    if until is None or until <= utcnow():
        return True
    raise JailedError(seconds_until(until), user.jail_bail_cost if user else 0)


def not_jailed() -> Any:
    """Prefix командыг шоронгоос хамгаалах decorator."""
    return commands.check(check_not_jailed)


async def check_is_admin(interaction: Any) -> bool:
    """Slash admin команд: Administrator эсвэл bot owner."""
    user = interaction.user
    if interaction.guild is None:
        raise app_commands.CheckFailure("✦ Энэ команд зөвхөн сервер дээр ажиллана.")
    if (
        getattr(user, "guild_permissions", None)
        and user.guild_permissions.administrator
    ):
        return True
    if await interaction.client.is_owner(user):
        return True
    raise app_commands.CheckFailure("✦ Энэ команд зөвхөн администраторт нээлттэй.")


def is_admin() -> Any:
    """Slash admin командын decorator."""
    return app_commands.check(check_is_admin)
