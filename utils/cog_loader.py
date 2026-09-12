"""Discovery for discord.py extensions.

Keeping discovery outside ``main.py`` makes it independently testable and
removes the manually maintained list that used to drift from ``cogs/``.
"""

from pathlib import Path
from typing import List


def discover_cogs(cogs_dir: Path) -> List[str]:
    """Return deterministic extension names for public Python files."""
    if not cogs_dir.is_dir():
        raise FileNotFoundError(f"Cog directory does not exist: {cogs_dir}")
    return sorted(
        path.stem
        for path in cogs_dir.glob("*.py")
        if not path.name.startswith("_")
    )
