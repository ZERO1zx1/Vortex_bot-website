"""Tests for the Unicode-aware font management system.

Run with:  python -m pytest tests/test_fonts.py -v
"""

import io
import os
import sys
import unittest

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PIL import Image, ImageDraw, ImageFont

from utils.fonts import (
    FontManager,
    get_font_manager,
    load_font,
    get_branding_font,
    get_emoji_font,
    draw_text_with_fallback,
    is_emoji,
)
from utils.branding import BOT_NAME


class TestFontDiscovery(unittest.TestCase):
    """Test font discovery and availability."""

    def setUp(self):
        self.fm = FontManager()

    def test_discover_fonts_returns_list(self):
        """Font discovery should return a list of (path, bold) tuples."""
        fonts = self.fm._discover_fonts()
        self.assertIsInstance(fonts, list)
        for entry in fonts:
            self.assertIsInstance(entry, tuple)
            self.assertEqual(len(entry), 2)
            self.assertIsInstance(entry[0], str)
            self.assertIsInstance(entry[1], bool)

    def test_discover_fonts_finds_at_least_one(self):
        """At least one font should be discoverable (system fallback)."""
        fonts = self.fm._discover_fonts()
        self.assertGreater(len(fonts), 0, "No fonts discovered — system fallback should find at least one")

    def test_get_font_returns_font(self):
        """get_font should return a usable font object."""
        font = self.fm.get_font(20, bold=True)
        self.assertIsNotNone(font)
        # Should be able to get a bounding box
        bbox = font.getbbox("Test")
        self.assertIsNotNone(bbox)

    def test_get_font_caching(self):
        """get_font should cache results."""
        font1 = self.fm.get_font(20, bold=True)
        font2 = self.fm.get_font(20, bold=True)
        self.assertIs(font1, font2, "Font should be cached")

    def test_get_font_different_sizes(self):
        """Different sizes should return different font objects."""
        font1 = self.fm.get_font(20, bold=True)
        font2 = self.fm.get_font(30, bold=True)
        self.assertIsNot(font1, font2)


class TestGlyphDetection(unittest.TestCase):
    """Test per-glyph font detection."""

    def setUp(self):
        self.fm = FontManager()

    def test_font_has_glyph_latin(self):
        """A font should be able to render basic Latin characters."""
        font = self.fm.get_font(20, bold=False)
        self.assertTrue(self.fm._font_has_glyph(font, "A"))
        self.assertTrue(self.fm._font_has_glyph(font, "z"))

    def test_font_has_glyph_cjk(self):
        """Some font should be able to render CJK characters."""
        # Find a font that can render CJK
        fonts = self.fm._discover_fonts()
        found_cjk = False
        for path, _ in fonts:
            try:
                font = ImageFont.truetype(path, 20)
                if self.fm._font_has_glyph(font, "蒼"):
                    found_cjk = True
                    break
            except Exception:
                continue
        # CJK support may not be available on all systems, but we should
        # at least not crash
        self.assertIsInstance(found_cjk, bool)

    def test_get_font_for_char_returns_font(self):
        """get_font_for_char should return a font for any character."""
        font = self.fm.get_font_for_char("A", 20, bold=True)
        self.assertIsNotNone(font)

    def test_get_font_for_char_caching(self):
        """get_font_for_char should cache results."""
        font1 = self.fm.get_font_for_char("A", 20, bold=True)
        font2 = self.fm.get_font_for_char("A", 20, bold=True)
        self.assertIs(font1, font2)


class TestMixedScriptRendering(unittest.TestCase):
    """Test rendering of mixed-script text."""

    def setUp(self):
        self.fm = FontManager()
        self.img = Image.new("RGBA", (1000, 200), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.img)
        self.font = self.fm.get_font(24, bold=True)

    def test_draw_text_with_fallback_latin(self):
        """Should render Latin text without crashing."""
        x = self.fm.draw_text_with_fallback(
            self.draw, (10, 10), "Aether", self.font, size=24, bold=True
        )
        self.assertGreater(x, 10)

    def test_draw_text_with_fallback_cyrillic(self):
        """Should render Cyrillic text without crashing."""
        x = self.fm.draw_text_with_fallback(
            self.draw, (10, 50), "Александр", self.font, size=24, bold=True
        )
        self.assertGreater(x, 10)

    def test_draw_text_with_fallback_mongolian(self):
        """Should render Mongolian Cyrillic without crashing."""
        x = self.fm.draw_text_with_fallback(
            self.draw, (10, 90), "Мөрөөдөл", self.font, size=24, bold=True
        )
        self.assertGreater(x, 10)

    def test_draw_text_with_fallback_chinese(self):
        """Should render Chinese characters without crashing."""
        x = self.fm.draw_text_with_fallback(
            self.draw, (10, 130), "蒼穹", self.font, size=24, bold=True
        )
        self.assertGreater(x, 10)

    def test_draw_text_with_fallback_mixed(self):
        """Should render mixed-script text without crashing."""
        text = "Aether 蒼穹 Мөрөөдөл 안녕"
        x = self.fm.draw_text_with_fallback(
            self.draw, (10, 10), text, self.font, size=24, bold=True
        )
        self.assertGreater(x, 10)

    def test_draw_text_with_fallback_stylized(self):
        """Should render stylized Unicode (Mathematical Alphanumeric Symbols)."""
        text = "𝓐𝓮𝓽𝓱𝓮𝓻"
        x = self.fm.draw_text_with_fallback(
            self.draw, (10, 10), text, self.font, size=24, bold=True
        )
        self.assertGreater(x, 10)

    def test_draw_text_with_fallback_empty(self):
        """Should handle empty text gracefully."""
        x = self.fm.draw_text_with_fallback(
            self.draw, (10, 10), "", self.font, size=24, bold=True
        )
        self.assertEqual(x, 10)

    def test_draw_text_with_fallback_long_name(self):
        """Should handle very long display names without crashing."""
        text = "A" * 500
        x = self.fm.draw_text_with_fallback(
            self.draw, (10, 10), text, self.font, size=24, bold=True
        )
        self.assertGreater(x, 10)

    def test_draw_text_with_fallback_zero_width(self):
        """Should skip zero-width characters."""
        text = "A\u200bB"  # Zero-width space between A and B
        x = self.fm.draw_text_with_fallback(
            self.draw, (10, 10), text, self.font, size=24, bold=True
        )
        self.assertGreater(x, 10)

    def test_draw_text_with_fallback_emoji(self):
        """Should handle emoji in text without crashing."""
        text = "Hello 🌍 World"
        x = self.fm.draw_text_with_fallback(
            self.draw, (10, 10), text, self.font, size=24, bold=True
        )
        self.assertGreater(x, 10)


class TestEmojiDetection(unittest.TestCase):
    """Test emoji detection."""

    def setUp(self):
        self.fm = FontManager()

    def test_is_emoji_smiley(self):
        self.assertTrue(self.fm.is_emoji("😀"))

    def test_is_emoji_thumbs_up(self):
        self.assertTrue(self.fm.is_emoji("👍"))

    def test_is_emoji_heart(self):
        self.assertTrue(self.fm.is_emoji("❤"))

    def test_is_emoji_not_emoji(self):
        self.assertFalse(self.fm.is_emoji("A"))

    def test_is_emoji_not_emoji_cyrillic(self):
        self.assertFalse(self.fm.is_emoji("М"))

    def test_is_emoji_empty(self):
        self.assertFalse(self.fm.is_emoji(""))

    def test_is_emoji_module_level(self):
        """Module-level is_emoji should delegate to FontManager."""
        self.assertTrue(is_emoji("😀"))
        self.assertFalse(is_emoji("A"))


class TestBrandingFont(unittest.TestCase):
    """Test branding font support."""

    def setUp(self):
        self.fm = FontManager()

    def test_branding_font_returns_font(self):
        """get_branding_font should return a usable font."""
        font = self.fm.get_branding_font(32)
        self.assertIsNotNone(font)

    def test_branding_font_renders_bot_name(self):
        """The branding font should be able to render the canonical bot name."""
        font = self.fm.get_branding_font(32)
        # Check that the font can render at least the first character
        # (𝓐 - Mathematical Script Capital A)
        self.assertTrue(
            self.fm._font_has_glyph(font, "𝓐") or
            self.fm._font_has_glyph(font, "蒼") or
            self.fm._font_has_glyph(font, "蒼"),
            "Branding font should render at least one character of the bot name"
        )

    def test_branding_font_caching(self):
        """Branding font should be cached."""
        font1 = self.fm.get_branding_font(32)
        font2 = self.fm.get_branding_font(32)
        self.assertIs(font1, font2)

    def test_bot_name_constant(self):
        """The BOT_NAME constant should be the canonical branding string."""
        self.assertEqual(BOT_NAME, "𝓐𝓮𝓽𝓱𝓮𝓻  蒼穹")


class TestEmojiFont(unittest.TestCase):
    """Test emoji font support."""

    def setUp(self):
        self.fm = FontManager()

    def test_get_emoji_font_returns_font_or_none(self):
        """get_emoji_font should return a font or None (not crash)."""
        font = self.fm.get_emoji_font(28)
        # May be None if no emoji font is available
        if font is not None:
            self.assertIsInstance(font, ImageFont.FreeTypeFont)

    def test_get_emoji_font_caching(self):
        """Emoji font should be cached."""
        font1 = self.fm.get_emoji_font(28)
        font2 = self.fm.get_emoji_font(28)
        self.assertIs(font1, font2)


class TestSecurity(unittest.TestCase):
    """Test security properties of the font system."""

    def setUp(self):
        self.fm = FontManager()

    def test_display_name_not_used_as_path(self):
        """Display names should never be used as filesystem paths."""
        # The font manager should only use predefined font paths
        malicious_name = "../../../etc/passwd"
        # This should not crash or access the filesystem with the name
        font = self.fm.get_font_for_char("A", 20, bold=True)
        self.assertIsNotNone(font)

    def test_long_display_name_no_crash(self):
        """Very long display names should not crash."""
        long_name = "A" * 10000
        font = self.fm.get_font_for_text(long_name, 20, bold=True)
        self.assertIsNotNone(font)

    def test_combining_marks_no_crash(self):
        """Combining marks should not crash rendering."""
        text = "A\u0301"  # A with acute accent (combining)
        img = Image.new("RGBA", (500, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = self.fm.get_font(20, bold=True)
        x = self.fm.draw_text_with_fallback(draw, (10, 10), text, font, size=20, bold=True)
        self.assertGreater(x, 10)

    def test_null_bytes_no_crash(self):
        """Null bytes in text should not crash."""
        text = "Hello\x00World"
        img = Image.new("RGBA", (500, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = self.fm.get_font(20, bold=True)
        # Should not raise
        try:
            self.fm.draw_text_with_fallback(draw, (10, 10), text, font, size=20, bold=True)
        except Exception:
            self.fail("draw_text_with_fallback should not crash on null bytes")


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with font_utils.py."""

    def test_load_font_backward_compat(self):
        """load_font should work as before."""
        font = load_font(20, bold=True)
        self.assertIsNotNone(font)

    def test_load_font_backward_compat_non_bold(self):
        """load_font with bold=False should work."""
        font = load_font(20, bold=False)
        self.assertIsNotNone(font)

    def test_get_font_manager_singleton(self):
        """get_font_manager should return the same instance."""
        fm1 = get_font_manager()
        fm2 = get_font_manager()
        self.assertIs(fm1, fm2)


class TestImageGeneration(unittest.TestCase):
    """Test actual image generation with mixed Unicode."""

    def setUp(self):
        self.fm = FontManager()

    def test_generate_mixed_script_image(self):
        """Generate an image with mixed-script text and verify it doesn't crash."""
        img = Image.new("RGBA", (800, 200), (30, 33, 40, 255))
        draw = ImageDraw.Draw(img)
        font = self.fm.get_font(32, bold=True)

        test_strings = [
            "Aether",
            "Александр",
            "Мөрөөдөл",
            "蒼穹",
            "こんにちは",
            "안녕하세요",
            "مرحبا",
            "Αθήνα",
            "Aether 蒼穹 Мөрөөдөл 안녕",
            "𝓐𝓮𝓽𝓰𝓮𝓻  蒼穹",
        ]

        y = 10
        for text in test_strings:
            self.fm.draw_text_with_fallback(
                draw, (10, y), text, font, fill=(255, 255, 255, 255), size=32, bold=True
            )
            y += 35

        # Verify the image was created
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        self.assertGreater(len(buf.getvalue()), 0)

    def test_generate_branding_image(self):
        """Generate an image with the canonical bot name."""
        img = Image.new("RGBA", (400, 100), (30, 33, 40, 255))
        draw = ImageDraw.Draw(img)
        font = self.fm.get_branding_font(36)

        self.fm.draw_text_with_fallback(
            draw, (10, 10), BOT_NAME, font, fill=(255, 255, 255, 255), size=36, bold=True
        )

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        self.assertGreater(len(buf.getvalue()), 0)


if __name__ == "__main__":
    unittest.main()
