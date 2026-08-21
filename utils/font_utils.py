"""Backward-compatible font utilities.

This module now delegates to the centralized Unicode-aware font manager in
``utils/fonts.py``.  Existing imports of ``load_font``, ``list_fonts``, and
``find_font`` continue to work, but new code should import directly from
``utils.fonts``.
"""

import os
from typing import List, Optional

from PIL import ImageFont

from utils.fonts import (
    FontManager,
    get_font_manager,
    load_font,
    get_branding_font,
    get_emoji_font,
    draw_text_with_fallback,
    is_emoji,
)

# Re-export for backward compatibility
__all__ = [
    "load_font",
    "list_fonts",
    "find_font",
    "get_branding_font",
    "get_emoji_font",
    "draw_text_with_fallback",
    "is_emoji",
    "FontManager",
    "get_font_manager",
]

# Keep the original FONTS_DIR for backward compatibility
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")


def list_fonts() -> List[str]:
    """List all available .ttf and .otf fonts in the assets directory."""
    fonts = []
    if os.path.isdir(FONTS_DIR):
        for f in os.listdir(FONTS_DIR):
            if f.lower().endswith((".ttf", ".otf", ".ttc")):
                fonts.append(f)
    return fonts


def find_font(name: str) -> Optional[str]:
    """Find a font by name in the assets directory."""
    if os.path.isdir(FONTS_DIR):
        for f in os.listdir(FONTS_DIR):
            if name.lower() in f.lower():
                return os.path.join(FONTS_DIR, f)
    return None
