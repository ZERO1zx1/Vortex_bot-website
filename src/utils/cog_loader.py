"""Discovery for discord.py extensions.

Keeping discovery outside ``main.py`` makes it independently testable and
removes the manually maintained list that used to drift from ``cogs/``.
"""

from pathlib import Path
from typing import Collection, List, Optional


# Public product surface for Aether.  These are the member-facing systems the
# bot intentionally registers.  The small set of foundation cogs contains no
# competing feature commands; it supplies navigation, presence and
# safe server administration for the selected systems.
ACTIVE_COGS = frozenset({
    "admin", "automod", "carts", "casino", "confessions", "economy",
    "fun", "games", "giveaway", "greetings", "help",
    "leaderboard", "leveling", "marriage", "menu", "moderation",
    "presence", "shop", "tickets", "webhooks",
})


def discover_cogs(cogs_dir: Path, enabled: Optional[Collection[str]] = None) -> List[str]:
    """Return deterministic extension names, optionally restricted to a manifest.

    Keeping disabled cogs on disk makes the cleanup reversible while ensuring
    their slash commands are not registered at startup.
    """
    if not cogs_dir.is_dir():
        raise FileNotFoundError(f"Cog directory does not exist: {cogs_dir}")
    return sorted(
        path.stem
        for path in cogs_dir.glob("*.py")
        if not path.name.startswith("_") and (enabled is None or path.stem in enabled)
    )
