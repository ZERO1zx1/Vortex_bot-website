"""Deploy-compatibility shim for the src/ refactor.

The bot's real entry point moved to ``src.main`` (src/main.py). Some deploy
platforms (e.g. Railway) still run ``python main.py`` via an overridden start
command in the service settings.  This shim re-invokes the real entry point so
BOTH ``python main.py`` and ``python -m src.main`` work identically.
"""
import os
import runpy
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

runpy.run_module("src.main", run_name="__main__")