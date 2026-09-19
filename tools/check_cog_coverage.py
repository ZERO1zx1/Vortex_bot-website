import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.utils.cog_loader import discover_cogs  # noqa: E402

from pathlib import Path
COGS_DIR = Path(ROOT) / 'src' / 'cogs'
loaded = set(discover_cogs(COGS_DIR))
disk = {f[:-3] for f in os.listdir(COGS_DIR) if f.endswith('.py') and f != '__init__.py'}
print('main.py discovers:', len(loaded), 'cogs | on disk:', len(disk))
print('on disk but NOT loaded:', sorted(disk - loaded))
print('listed but missing file:', sorted(loaded - disk))