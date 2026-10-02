"""Backward-compatible font utilities.

This module now delegates to the centralized Unicode-aware font manager in
``utils/fonts.py``.  Existing imports of ``load_font``, ``list_fonts``, and
``find_font`` continue to work, but new code should import directly from
``utils.fonts``.
"""

import os
from pathlib import Path

from src.utils.fonts import (
    FontManager,
    draw_text_with_fallback,
    get_branding_font,
    get_emoji_font,
    get_font_manager,
    is_emoji,
    load_font,
)

# Re-export for backward compatibility
__all__ = [
    "FontManager",
    "draw_text_with_fallback",
    "find_font",
    "get_branding_font",
    "get_emoji_font",
    "get_font_manager",
    "is_emoji",
    "list_fonts",
    "load_font",
]

# Keep the original FONTS_DIR for backward compatibility
ASSETS_DIR = str(Path(__file__).resolve().parents[2] / "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")


def list_fonts() -> list[str]:
    """List all available .ttf and .otf fonts in the assets directory."""
    fonts = []
    if os.path.isdir(FONTS_DIR):
        for f in os.listdir(FONTS_DIR):
            if f.lower().endswith((".ttf", ".otf", ".ttc")):
                fonts.append(f)
    return fonts


def find_font(name: str) -> str | None:
    """Find a font by name in the assets directory."""
    if os.path.isdir(FONTS_DIR):
        for f in os.listdir(FONTS_DIR):
            if name.lower() in f.lower():
                return os.path.join(FONTS_DIR, f)
    return None
