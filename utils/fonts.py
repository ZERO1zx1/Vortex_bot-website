"""Centralized Unicode-aware font management with per-glyph fallback.

This module provides a FontManager that maintains an ordered fallback chain
of fonts capable of rendering a wide range of Unicode scripts.  It supports
per-glyph fallback so that mixed-script Discord display names render correctly
inside the same text run.

Design goals
------------
* Never crash the bot when an optional font is unavailable.
* Cache font/glyph lookups to avoid repeated filesystem scans.
* Support emoji separately from normal text.
* Keep branding font selection separate from user-generated text.
* Do NOT download or commit large font collections.
"""

from __future__ import annotations

import logging
import os
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from PIL import ImageDraw, ImageFont

log = logging.getLogger("aether.fonts")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

# ---------------------------------------------------------------------------
# Font fallback chain (ordered by priority)
# ---------------------------------------------------------------------------
# Each entry is (font_filename_or_path, is_bold).
# The chain is searched in order; the first font that contains a glyph wins.
#
# Noto families are preferred because they cover the widest Unicode range.
# System fonts are used as a last resort on each platform.
#
# On Windows, common Noto fonts may be installed at:
#   C:/Windows/Fonts/
# On Linux, DejaVu and Noto are typically at:
#   /usr/share/fonts/truetype/
#
# We do NOT hardcode a single path — we search multiple locations.

# Primary font candidates (broad Unicode coverage)
_FONT_CANDIDATES: List[Tuple[str, bool]] = [
    # Project-bundled fonts
    ("levelfont.otf", True),
    ("levelfont.otf", False),
    # Noto Sans (CJK, Latin, Cyrillic, etc.)
    ("NotoSans-Regular.ttf", False),
    ("NotoSans-Bold.ttf", True),
    ("NotoSansCJK-Regular.ttc", False),
    ("NotoSansCJK-Bold.ttc", True),
    ("NotoSansCJKsc-Regular.otf", False),
    ("NotoSansCJKsc-Bold.otf", True),
    ("NotoSansJP-Regular.otf", False),
    ("NotoSansKR-Regular.otf", False),
    ("NotoSansArabic-Regular.ttf", False),
    ("NotoSansHebrew-Regular.ttf", False),
    ("NotoSansThai-Regular.ttf", False),
    ("NotoSansDevanagari-Regular.ttf", False),
    # Noto Symbols (emoji-adjacent symbols, math, etc.)
    ("NotoSansSymbols-Regular.ttf", False),
    ("NotoSansSymbols2-Regular.ttf", False),
    # DejaVu (good Unicode coverage, commonly available)
    ("DejaVuSans.ttf", False),
    ("DejaVuSans-Bold.ttf", True),
    ("DejaVuSansMono.ttf", False),
    # System fonts (Windows)
    ("C:/Windows/Fonts/arial.ttf", False),
    ("C:/Windows/Fonts/arialbd.ttf", True),
    ("C:/Windows/Fonts/msyh.ttc", False),       # Microsoft YaHei (CJK)
    ("C:/Windows/Fonts/msyhbd.ttc", True),      # Microsoft YaHei Bold
    # System fonts (Linux)
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", False),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", True),
    ("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", False),
    ("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", True),
]

# Emoji font candidates (color emoji support is limited in Pillow)
_EMOJI_FONT_CANDIDATES: List[str] = [
    "C:/Windows/Fonts/seguiemj.ttf",           # Segoe UI Emoji (Windows)
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


class FontManager:
    """Manages font discovery, caching, and per-glyph fallback rendering."""

    def __init__(self) -> None:
        self._font_cache: Dict[Any, Any] = {}
        self._glyph_cache: Dict[Tuple[int, str], bool] = {}
        self._available_fonts: Optional[List[Tuple[str, bool]]] = None
        self._available_emoji_fonts: Optional[List[str]] = None

    # ------------------------------------------------------------------
    # Font discovery
    # ------------------------------------------------------------------
    def _discover_fonts(self) -> List[Tuple[str, bool]]:
        """Discover available fonts from assets dir and system paths."""
        if self._available_fonts is not None:
            return self._available_fonts

        found: List[Tuple[str, bool]] = []
        seen_paths: set = set()

        # 1. Check assets/fonts directory
        if os.path.isdir(FONTS_DIR):
            for fname in sorted(os.listdir(FONTS_DIR)):
                fpath = os.path.join(FONTS_DIR, fname)
                if not os.path.isfile(fpath):
                    continue
                if not fname.lower().endswith((".ttf", ".otf", ".ttc")):
                    continue
                if fpath in seen_paths:
                    continue
                seen_paths.add(fpath)
                is_bold = "bold" in fname.lower()
                found.append((fpath, is_bold))

        # 2. Check assets root for levelfont.otf
        lf = os.path.join(ASSETS_DIR, "levelfont.otf")
        if os.path.isfile(lf) and lf not in seen_paths:
            seen_paths.add(lf)
            found.append((lf, True))

        # 3. Check candidate system paths
        for path, is_bold in _FONT_CANDIDATES:
            if path in seen_paths:
                continue
            if os.path.isfile(path):
                seen_paths.add(path)
                found.append((path, is_bold))

        # 4. Fallback: scan common system font directories
        system_dirs = [
            "C:/Windows/Fonts",
            "/usr/share/fonts/truetype",
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.local/share/fonts"),
            os.path.expanduser("~/.fonts"),
        ]
        for sdir in system_dirs:
            if not os.path.isdir(sdir):
                continue
            try:
                for fname in os.listdir(sdir):
                    fpath = os.path.join(sdir, fname)
                    if fpath in seen_paths:
                        continue
                    if not fname.lower().endswith((".ttf", ".otf", ".ttc")):
                        continue
                    if not os.path.isfile(fpath):
                        continue
                    seen_paths.add(fpath)
                    is_bold = "bold" in fname.lower() or "bd" in fname.lower()
                    found.append((fpath, is_bold))
            except (PermissionError, OSError):
                continue

        self._available_fonts = found
        log.debug("Discovered %d fonts", len(found))
        return found

    def _discover_emoji_fonts(self) -> List[str]:
        """Discover available emoji-capable fonts."""
        if self._available_emoji_fonts is not None:
            return self._available_emoji_fonts

        found: List[str] = []
        seen: set = set()

        for path in _EMOJI_FONT_CANDIDATES:
            if path in seen:
                continue
            if os.path.isfile(path):
                seen.add(path)
                found.append(path)

        # Scan system dirs for emoji fonts
        for sdir in ["C:/Windows/Fonts", "/usr/share/fonts/truetype/noto", "/usr/share/fonts"]:
            if not os.path.isdir(sdir):
                continue
            try:
                for fname in os.listdir(sdir):
                    fpath = os.path.join(sdir, fname)
                    if fpath in seen:
                        continue
                    if not fname.lower().endswith((".ttf", ".otf", ".ttc")):
                        continue
                    if not os.path.isfile(fpath):
                        continue
                    lower = fname.lower()
                    if "emoji" in lower or "seguiemj" in lower:
                        seen.add(fpath)
                        found.append(fpath)
            except (PermissionError, OSError):
                continue

        self._available_emoji_fonts = found
        return found

    # ------------------------------------------------------------------
    # Font loading with caching
    # ------------------------------------------------------------------
    def get_font(self, size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
        """Get a font for general text.  Returns a cached FreeTypeFont.

        Falls back to Pillow's default bitmap font if no TrueType font is found.
        """
        key = ("__default__", size, bold)
        if key in self._font_cache:
            return self._font_cache[key]

        fonts = self._discover_fonts()
        for path, is_bold in fonts:
            if is_bold == bold:
                try:
                    font = ImageFont.truetype(path, size)
                    self._font_cache[key] = font
                    return font
                except Exception as e:
                    log.debug("Failed to load font %s: %s", path, e)
                    continue

        # Fallback: try any font regardless of bold flag
        for path, _ in fonts:
            try:
                font = ImageFont.truetype(path, size)
                self._font_cache[key] = font
                return font
            except Exception:
                continue

        # Last resort: Pillow default
        try:
            font = ImageFont.load_default(size)
        except TypeError:
            font = ImageFont.load_default()
        self._font_cache[key] = font
        return font  # type: ignore[return-value]

    def get_branding_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Get a font suitable for the canonical bot name 𝓐𝓮𝓽𝓱𝓮𝓻  蒼穹.

        The bot name uses Mathematical Alphanumeric Symbols (U+1D4D0–U+1D7FF)
        and CJK Unified Ideographs (U+87F3, U+7A7A).  We try the project's
        levelfont.otf first, then fall back to any font that contains the
        required glyphs.
        """
        key = ("__branding__", size, True)
        if key in self._font_cache:
            return self._font_cache[key]

        # Try levelfont.otf first (project asset)
        lf = os.path.join(ASSETS_DIR, "levelfont.otf")
        if os.path.isfile(lf):
            try:
                font = ImageFont.truetype(lf, size)
                # Verify it can render the bot name
                if self._font_has_glyph(font, "𝓐"):
                    self._font_cache[key] = font
                    return font
            except Exception:
                pass

        # Try any font that can render the bot name
        from utils.branding import BOT_NAME
        fonts = self._discover_fonts()
        for path, _ in fonts:
            try:
                font = ImageFont.truetype(path, size)
                if self._font_has_glyph(font, BOT_NAME):
                    self._font_cache[key] = font
                    return font
            except Exception:
                continue

        # Fallback to default
        font = self.get_font(size, bold=True)
        self._font_cache[key] = font
        return font

    def get_emoji_font(self, size: int) -> Optional[ImageFont.FreeTypeFont]:
        """Get a font for emoji rendering.  Returns None if no emoji font found."""
        key = ("__emoji__", size, False)
        if key in self._font_cache:
            cached = self._font_cache[key]
            return cached if cached is not None else None

        emoji_fonts = self._discover_emoji_fonts()
        for path in emoji_fonts:
            try:
                font = ImageFont.truetype(path, size)
                self._font_cache[key] = font
                return font
            except Exception:
                continue

        self._font_cache[key] = None
        return None

    # ------------------------------------------------------------------
    # Glyph detection
    # ------------------------------------------------------------------
    def _font_has_glyph(self, font: ImageFont.FreeTypeFont, char: str) -> bool:
        """Check if a font contains a specific character/glyph."""
        if not char:
            return True
        cache_key = (id(font), char)
        if cache_key in self._glyph_cache:
            return self._glyph_cache[cache_key]

        try:
            # Pillow 10+ uses getbbox; older uses getmask
            if hasattr(font, "getbbox"):
                bbox = font.getbbox(char)
                result = bbox is not None and bbox[2] > 0 and bbox[3] > 0
            else:
                mask = font.getmask(char)
                result = mask is not None and mask.size > 0
        except Exception:
            result = False

        self._glyph_cache[cache_key] = result
        return result

    def _font_has_glyphs(self, font: ImageFont.FreeTypeFont, text: str) -> bool:
        """Check if a font contains all characters in text."""
        for ch in text:
            if not self._font_has_glyph(font, ch):
                return False
        return True

    # ------------------------------------------------------------------
    # Per-glyph fallback rendering
    # ------------------------------------------------------------------
    def get_font_for_char(self, char: str, size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
        """Get the best font for a single character.

        Searches the fallback chain and returns the first font that
        contains the glyph for *char*.
        """
        if not char:
            return self.get_font(size, bold)

        cache_key = ("__char__", char, size, bold)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        fonts = self._discover_fonts()
        for path, is_bold in fonts:
            if is_bold != bold:
                continue
            try:
                font = ImageFont.truetype(path, size)
                if self._font_has_glyph(font, char):
                    self._font_cache[cache_key] = font
                    return font
            except Exception:
                continue

        # Try any font regardless of bold
        for path, _ in fonts:
            try:
                font = ImageFont.truetype(path, size)
                if self._font_has_glyph(font, char):
                    self._font_cache[cache_key] = font
                    return font
            except Exception:
                continue

        # Fallback to default
        font = self.get_font(size, bold)
        self._font_cache[cache_key] = font
        return font

    def get_font_for_text(self, text: str, size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
        """Get a font that can render all characters in *text*.

        If no single font covers all characters, returns the primary font
        (callers should use draw_text_with_fallback for per-glyph rendering).
        """
        if not text:
            return self.get_font(size, bold)

        cache_key = ("__text__", text, size, bold)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        fonts = self._discover_fonts()
        for path, is_bold in fonts:
            if is_bold != bold:
                continue
            try:
                font = ImageFont.truetype(path, size)
                if self._font_has_glyphs(font, text):
                    self._font_cache[cache_key] = font
                    return font
            except Exception:
                continue

        # No single font covers everything — return primary font
        # Callers should use draw_text_with_fallback for mixed-script text
        font = self.get_font(size, bold)
        self._font_cache[cache_key] = font
        return font

    # ------------------------------------------------------------------
    # Multi-font text rendering
    # ------------------------------------------------------------------
    def draw_text_with_fallback(
        self,
        draw: ImageDraw.ImageDraw,
        xy: Tuple[int, int],
        text: str,
        font: ImageFont.FreeTypeFont,
        fill: Tuple[int, int, int, int] = (255, 255, 255, 255),
        size: int = 20,
        bold: bool = True,
    ) -> int:
        """Draw text with per-glyph font fallback.

        Groups adjacent characters that share the same font into runs,
        then renders each run sequentially.  Returns the final x position.

        This is the primary method for rendering Discord display names that
        may contain mixed Unicode scripts.
        """
        if not text:
            return xy[0]

        x = xy[0]
        y = xy[1]

        # Group characters into runs by font
        runs: List[Tuple[Optional[ImageFont.FreeTypeFont], str]] = []
        current_font: Optional[ImageFont.FreeTypeFont] = None
        current_run = ""

        for ch in text:
            # Skip zero-width characters
            if ch in ("\u200b", "\u200c", "\u200d", "\ufeff"):
                continue

            # Check if current font can render this char
            if current_font is not None and self._font_has_glyph(current_font, ch):
                current_run += ch
            else:
                # Flush current run
                if current_run:
                    runs.append((current_font, current_run))

                # Find a font for this char
                current_font = self.get_font_for_char(ch, size, bold)
                current_run = ch

        # Flush last run
        if current_run:
            runs.append((current_font, current_run))

        # Render each run
        for run_font, run_text in runs:
            if run_font is None:
                run_font = font
            draw.text((x, y), run_text, font=run_font, fill=fill)
            bbox = draw.textbbox((x, y), run_text, font=run_font)
            x = int(bbox[2])  # advance to end of this run

        return x

    # ------------------------------------------------------------------
    # Emoji detection
    # ------------------------------------------------------------------
    def is_emoji(self, ch: str) -> bool:
        """Check if a character is an emoji."""
        if not ch:
            return False

        # Check Unicode ranges first (most reliable for emoji detection)
        cp = ord(ch)
        emoji_ranges = [
            (0x1F600, 0x1F64F),   # Emoticons
            (0x1F300, 0x1F5FF),   # Misc Symbols and Pictographs
            (0x1F680, 0x1F6FF),   # Transport and Map
            (0x1F1E0, 0x1F1FF),   # Flags
            (0x1F900, 0x1F9FF),   # Supplemental Symbols
            (0x1FA00, 0x1FA6F),   # Chess Symbols
            (0x1FA70, 0x1FAFF),   # Symbols and Pictographs Extended-A
            (0x2600, 0x26FF),     # Misc Symbols
            (0x2700, 0x27BF),     # Dingbats
            (0xFE00, 0xFE0F),     # Variation Selectors
            (0x1F004, 0x1F004),   # Mahjong
            (0x1F0CF, 0x1F0CF),   # Playing Card
        ]
        for start, end in emoji_ranges:
            if start <= cp <= end:
                return True

        # Secondary check: Unicode name
        try:
            name = unicodedata.name(ch)
            return "EMOJI" in name or "PICTOGRA" in name
        except ValueError:
            pass

        return False

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def clear_cache(self) -> None:
        """Clear all cached fonts and glyph lookups."""
        self._font_cache.clear()
        self._glyph_cache.clear()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_font_manager: Optional[FontManager] = None


def get_font_manager() -> FontManager:
    """Get the singleton FontManager instance."""
    global _font_manager
    if _font_manager is None:
        _font_manager = FontManager()
    return _font_manager


# ---------------------------------------------------------------------------
# Backward-compatible API (delegates to FontManager)
# ---------------------------------------------------------------------------
def load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Backward-compatible font loader.  Delegates to FontManager."""
    return get_font_manager().get_font(size, bold)


def get_branding_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a font suitable for the canonical bot name."""
    return get_font_manager().get_branding_font(size)


def get_emoji_font(size: int) -> Optional[ImageFont.FreeTypeFont]:
    """Get a font for emoji rendering."""
    return get_font_manager().get_emoji_font(size)


def draw_text_with_fallback(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int, int] = (255, 255, 255, 255),
    size: int = 20,
    bold: bool = True,
) -> int:
    """Draw text with per-glyph font fallback.  Delegates to FontManager."""
    return get_font_manager().draw_text_with_fallback(
        draw, xy, text, font, fill, size, bold
    )


def is_emoji(ch: str) -> bool:
    """Check if a character is an emoji.  Delegates to FontManager."""
    return get_font_manager().is_emoji(ch)
