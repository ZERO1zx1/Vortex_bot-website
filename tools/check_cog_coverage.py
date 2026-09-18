import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.cog_loader import discover_cogs  # noqa: E402

from pathlib import Path
loaded = set(discover_cogs(Path('src') / 'cogs'))
disk = {f[:-3] for f in os.listdir('src/cogs') if f.endswith('.py') and f != '__init__.py'}
print('main.py discovers:', len(loaded), 'cogs | on disk:', len(disk))
print('on disk but NOT loaded:', sorted(disk - loaded))
print('listed but missing file:', sorted(loaded - disk))