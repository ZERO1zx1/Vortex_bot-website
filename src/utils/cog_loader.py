"""Discovery for discord.py extensions.

Keeping discovery outside ``main.py`` makes it independently testable and
removes the manually maintained list that used to drift from ``cogs/``.
"""

from collections.abc import Collection
from pathlib import Path

# Public product surface for Aether.  These are the member-facing systems the
# bot intentionally registers.  The small set of foundation cogs contains no
# competing feature commands; it supplies navigation, presence and
# safe server administration for the selected systems.
ACTIVE_COGS = frozenset({
    "admin.admin",
    "admin.automod",
    "admin.level_admin",
    "admin.moderation",
    "admin.webhooks",
    "economy.economy",
    "economy.government",
    "economy.leaderboard",
    "games.anime_clash",
    "games.casino",
    "games.counting",
    "games.fun",
    "games.games",
    "games.leveling",
    "games.pvp",
    "games.texas_poker",
    "community.confessions",
    "community.giveaway",
    "community.greetings",
    "community.marriage",
    "community.tickets",
    "shop.cafe",
    "shop.carts",
    "shop.shop",
    "shop.trade",
    "system.help",
    "system.menu",
    "system.presence",
})


def discover_cogs(cogs_dir: Path, enabled: Collection[str] | None = None) -> list[str]:
    """Return deterministic extension names, optionally restricted to a manifest.

    Keeping disabled cogs on disk makes the cleanup reversible while ensuring
    their slash commands are not registered at startup.
    """
    if not cogs_dir.is_dir():
        raise FileNotFoundError(f"Cog directory does not exist: {cogs_dir}")
    names = []
    for path in cogs_dir.rglob("*.py"):
        relative = path.relative_to(cogs_dir)
        if path.name.startswith("_") or any(part.startswith("_") for part in relative.parts[:-1]):
            continue
        extension = ".".join(relative.with_suffix("").parts)
        if enabled is None or extension in enabled:
            names.append(extension)
    # LevelAdmin needs the registered Leveling engine. Help prunes its catalog
    # against the command tree and therefore must load after both.
    return sorted(
        names,
        key=lambda name: (
            name == "system.help",
            name == "admin.level_admin",
            name,
        ),
    )
