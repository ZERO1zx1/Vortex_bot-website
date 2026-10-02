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
    "admin", "automod", "cafe", "carts", "casino", "confessions", "counting", "economy",
    "anime_clash", "fun", "games", "giveaway", "government", "greetings", "help",
    "leaderboard", "leveling", "level_admin", "marriage", "menu", "moderation",
    "presence", "pvp", "shop", "texas_poker", "tickets", "trade", "webhooks",
})


def discover_cogs(cogs_dir: Path, enabled: Collection[str] | None = None) -> list[str]:
    """Return deterministic extension names, optionally restricted to a manifest.

    Keeping disabled cogs on disk makes the cleanup reversible while ensuring
    their slash commands are not registered at startup.
    """
    if not cogs_dir.is_dir():
        raise FileNotFoundError(f"Cog directory does not exist: {cogs_dir}")
    names = [
        path.stem
        for path in cogs_dir.glob("*.py")
        if not path.name.startswith("_") and (enabled is None or path.stem in enabled)
    ]
    # LevelAdmin needs the registered Leveling engine. Help prunes its catalog
    # against the command tree and therefore must load after both.
    return sorted(names, key=lambda name: (name == "help", name == "level_admin", name))
