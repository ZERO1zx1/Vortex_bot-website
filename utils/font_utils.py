import os
from PIL import ImageFont

FONTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts"))

def load_font(size: int, bold: bool = True):
    """Load a bold or regular font from the fonts directory or system fallback."""
    if bold:
        candidates = ["DejaVu Sans Bold.ttf", "DejaVuSans-Bold.ttf"]
    else:
        candidates = ["DejaVuSans.ttf", "DejaVu Sans.ttf"]

    for name in candidates:
        path = os.path.join(FONTS_DIR, name)
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

    if os.path.isdir(FONTS_DIR):
        for fname in os.listdir(FONTS_DIR):
            if not fname.lower().endswith(".ttf"):
                continue
            is_bold_file = "bold" in fname.lower()
            if is_bold_file == bold:
                path = os.path.join(FONTS_DIR, fname)
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass

    # System fallback
    system_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in system_fonts:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

    return ImageFont.load_default()

def list_fonts():
    """List all available .ttf and .otf fonts in the assets directory."""
    fonts = []
    if os.path.isdir(FONTS_DIR):
        for f in os.listdir(FONTS_DIR):
            if f.lower().endswith((".ttf", ".otf")):
                fonts.append(f)
    return fonts

def find_font(name: str):
    """Find a font by name in the assets directory."""
    if os.path.isdir(FONTS_DIR):
        for f in os.listdir(FONTS_DIR):
            if name.lower() in f.lower():
                return os.path.join(FONTS_DIR, f)
    return None
