import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils.cog_loader import ACTIVE_COGS, discover_cogs

COGS_DIR = ROOT / "src" / "cogs"
loaded = set(discover_cogs(COGS_DIR, ACTIVE_COGS))
disk = set(discover_cogs(COGS_DIR))
print("main.py discovers:", len(loaded), "cogs | on disk:", len(disk))
print("on disk but NOT loaded:", sorted(disk - loaded))
print("listed but missing file:", sorted(ACTIVE_COGS - disk))

if loaded != ACTIVE_COGS or disk != ACTIVE_COGS:
    raise SystemExit(1)
