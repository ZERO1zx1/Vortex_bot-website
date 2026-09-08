"""Procedural explorer-journal art kit (Pillow only, zero image assets).

Produces the hand-drawn, illustrated look — parchment pages, wobbly ink
borders, watercolor progress bars, wax seals, tally marks, cross-hatched
slots, embroidered patches and stamp bursts — entirely in code so no binary
assets need to be committed.

All helpers are deterministic: every function takes a ``seed`` so the same
card renders pixel-identical across restarts (no flaky snapshot diffs).
"""

from __future__ import annotations

import logging
import math
import random

from PIL import Image, ImageDraw

log = logging.getLogger("aether.journal")

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
PARCHMENT_BASE = (233, 215, 174, 255)
PARCHMENT_DEEP = (206, 181, 133, 255)
INK = (62, 44, 28, 255)
INK_SOFT = (100, 77, 52, 255)
INK_FAINT = (130, 108, 80, 255)
WAX_RED = (178, 58, 44, 255)
WAX_DARK = (126, 35, 27, 255)
GOLD = (198, 142, 44, 255)
LEAF = (106, 148, 84, 255)
LEAF_DEEP = (66, 104, 54, 255)
RIVER = (84, 132, 168, 255)
RIVER_DEEP = (52, 92, 126, 255)
CHALK = (238, 236, 228, 255)
SLATE = (52, 56, 60, 255)
WOOD = (122, 84, 48, 255)
WOOD_DARK = (88, 58, 32, 255)

RARITY_COLORS = {
    "common": (150, 148, 140, 255),
    "uncommon": (106, 168, 84, 255),
    "rare": (84, 132, 220, 255),
    "epic": (150, 92, 200, 255),
    "legendary": (228, 168, 48, 255),
    "mythic": (214, 76, 76, 255),
}


def _rng(seed: int) -> random.Random:
    return random.Random(int(seed))


# ---------------------------------------------------------------------------
# Parchment page
# ---------------------------------------------------------------------------
def parchment(size, seed: int = 7, base=PARCHMENT_BASE) -> Image.Image:
    """Warm textured paper: grain + fibers + darkened edges."""
    w, h = size
    img = Image.new("RGBA", size, base)
    rng = _rng(seed)

    # Paper grain (small noise, scaled up for soft blotches).
    try:
        noise = Image.effect_noise((max(1, w // 3), max(1, h // 3)), 26)
        noise = noise.resize(size, Image.BILINEAR).convert("L")
        grain = Image.new("RGBA", size, (118, 92, 58, 255))
        grain.putalpha(noise.point(lambda v: int(v * 0.10)))
        img.alpha_composite(grain)
    except Exception as e:  # pragma: no cover - cosmetic only
        log.debug("parchment grain skipped: %s", e)

    # A few lighter blotches for a watercolor-wash feel.
    wash = Image.new("RGBA", size, (0, 0, 0, 0))
    wd = ImageDraw.Draw(wash)
    for i in range(5):
        x, y = rng.randint(0, w), rng.randint(0, h)
        r = rng.randint(min(w, h) // 6, min(w, h) // 3)
        wd.ellipse([x - r, y - r, x + r, y + r], fill=(255, 250, 235, 14))
    img.alpha_composite(wash)

    # Fibers: short faint strokes.
    fib = Image.new("RGBA", size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fib)
    for _ in range(60):
        x, y = rng.randint(0, w), rng.randint(0, h)
        ang = rng.uniform(0, math.pi)
        ln = rng.randint(6, 22)
        x2, y2 = x + math.cos(ang) * ln, y + math.sin(ang) * ln
        tone = (255, 250, 235, 26) if rng.random() < 0.5 else (150, 120, 80, 26)
        fd.line([(x, y), (x2, y2)], fill=tone, width=1)
    img.alpha_composite(fib)

    # Darkened page edges.
    edge = ImageDraw.Draw(img)
    for i in range(20):
        alpha = int(10 * (1 - i / 20))
        edge.rectangle([i, i, w - 1 - i, h - 1 - i], outline=(101, 74, 40, alpha))
    return img


# ---------------------------------------------------------------------------
# Wobbly ink lines / borders (the hand-drawn feel)
# ---------------------------------------------------------------------------
def wobble_line(draw: ImageDraw.ImageDraw, p0, p1, fill, width: int = 2,
                seed: int = 1, amp: float = 1.6, segs: int = 14) -> None:
    """Slightly imperfect line between two points (deterministic)."""
    rng = _rng(seed)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length, dx / length
    pts = []
    for i in range(segs + 1):
        t = i / segs
        off = rng.uniform(-amp, amp) if 0 < i < segs else 0.0
        pts.append((p0[0] + dx * t + nx * off, p0[1] + dy * t + ny * off))
    draw.line(pts, fill=fill, width=width, joint="curve")


def ink_border(draw: ImageDraw.ImageDraw, size, seed: int = 3,
               margin: int = 8, fill=INK, width: int = 3) -> None:
    """Double hand-drawn frame: bold outer line + thin inner line."""
    w, h = size
    corners = [(margin, margin), (w - margin, margin),
               (w - margin, h - margin), (margin, h - margin)]
    for i in range(4):
        wobble_line(draw, corners[i], corners[(i + 1) % 4],
                    fill, width, seed * 10 + i)
    inset = margin + 7
    inner = [(inset, inset), (w - inset, inset),
             (w - inset, h - inset), (inset, h - inset)]
    for i in range(4):
        wobble_line(draw, inner[i], inner[(i + 1) % 4],
                    INK_SOFT, 1, seed * 10 + 100 + i, amp=1.2)


def sketch_divider(draw: ImageDraw.ImageDraw, x0: int, x1: int, y: int,
                   seed: int = 5) -> None:
    """Wobbly horizontal rule with a diamond ornament in the middle."""
    wobble_line(draw, (x0, y), (x1, y), INK_SOFT, 2, seed)
    mid = (x0 + x1) // 2
    draw.polygon([(mid - 6, y), (mid, y - 6), (mid + 6, y), (mid, y + 6)],
                 outline=INK, width=2)


# ---------------------------------------------------------------------------
# Title banner (ribbon plate)
# ---------------------------------------------------------------------------
def banner(draw: ImageDraw.ImageDraw, box, text: str, font, seed: int = 9,
           fill=(247, 236, 210, 255), text_fill=INK) -> None:
    """Parchment ribbon with folded tails and ink outline."""
    x0, y0, x1, y1 = box
    mid_y = (y0 + y1) // 2
    tail = 16
    # Tails behind the plate.
    for side, torn in ((x0, -1), (x1, 1)):
        tx = side + torn * tail
        draw.polygon([(side, y0 + 4), (tx, mid_y), (side, y1 - 4)],
                     fill=PARCHMENT_DEEP, outline=INK)
    draw.rounded_rectangle(box, radius=8, fill=fill, outline=None)
    for i, (a, b) in enumerate((((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
                                ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0)))):
        wobble_line(draw, a, b, INK, 2, seed * 7 + i, amp=1.2)
    try:
        tw = draw.textlength(text, font=font)
    except AttributeError:  # pragma: no cover - old Pillow
        tw = draw.textsize(text, font=font)[0]
    draw.text(((x0 + x1 - tw) / 2, y0 + 3), text, font=font, fill=text_fill)


# ---------------------------------------------------------------------------
# Watercolor progress bar ("inked path")
# ---------------------------------------------------------------------------
def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def watercolor_bar(draw: ImageDraw.ImageDraw, box, progress: float,
                   fill_from=LEAF, fill_to=RIVER, seed: int = 11) -> None:
    """Gradient wash bar with speckles, highlight streak and ink outline."""
    x0, y0, x1, y1 = box
    progress = max(0.0, min(1.0, progress))
    h = y1 - y0
    draw.rounded_rectangle(box, radius=h // 2, fill=(74, 58, 40, 255))
    fill_w = int((x1 - x0) * progress)
    if fill_w > 2:
        slices = max(1, min(64, fill_w))
        for i in range(slices):
            t0, t1 = i / slices, (i + 1) / slices
            col = tuple(_lerp(fill_from[c], fill_to[c], (t0 + t1) / 2) for c in range(3)) + (255,)
            sx0 = x0 + int(fill_w * t0)
            sx1 = x0 + max(int(fill_w * t1), int(fill_w * t0) + 1)
            draw.rectangle([sx0, y0 + 2, min(sx1, x0 + fill_w), y1 - 2], fill=col)
        # Highlight streak (wet-ink shine).
        draw.rounded_rectangle([x0 + 4, y0 + 3, x0 + fill_w - 4, y0 + h // 3],
                               radius=4, fill=(255, 255, 255, 70))
        # Speckles.
        rng = _rng(seed)
        for _ in range(fill_w // 6):
            sx = rng.randint(x0 + 2, x0 + fill_w - 2)
            sy = rng.randint(y0 + 3, y1 - 3)
            draw.point((sx, sy), fill=(40, 30, 18, 90))
    # Wobbly ink outline on top.
    for i, (a, b) in enumerate((((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
                                ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0)))):
        wobble_line(draw, a, b, INK, 2, seed * 13 + i, amp=1.1, segs=16)


# ---------------------------------------------------------------------------
# Wax seal / stamp burst / embroidered patch
# ---------------------------------------------------------------------------
def wax_seal(draw: ImageDraw.ImageDraw, center, radius: int, text: str,
             font, seed: int = 21) -> None:
    """Hand-pressed seal: irregular edge, inner ring, centered text."""
    rng = _rng(seed)
    cx, cy = center
    pts = []
    for i in range(48):
        ang = 2 * math.pi * i / 48
        r = radius + rng.uniform(-2.5, 2.5)
        pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
    draw.polygon(pts, fill=WAX_RED, outline=WAX_DARK)
    draw.ellipse([cx - radius + 7, cy - radius + 7,
                  cx + radius - 7, cy + radius - 7], outline=(240, 200, 170, 255), width=2)
    try:
        tw = draw.textlength(text, font=font)
        th = font.size if hasattr(font, "size") else 20
    except AttributeError:  # pragma: no cover - old Pillow
        tw, th = draw.textsize(text, font=font)
    draw.text((cx - tw / 2, cy - th / 2 - 2), text, font=font, fill=(250, 235, 215, 255))


def stamp_burst(img: Image.Image, draw: ImageDraw.ImageDraw, center, r_outer: int,
                text: str, font, seed: int = 31, angle: float = -12.0) -> None:
    """Starburst celebration stamp (level-up press)."""
    cx, cy = center
    rng = _rng(seed)
    points, n = 14, []
    for i in range(points * 2):
        r = r_outer + rng.uniform(-3, 3) if i % 2 == 0 else r_outer * 0.72
        ang = math.pi * i / points
        n.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
    draw.polygon(n, fill=WAX_RED, outline=WAX_DARK)
    # Rotated caption on its own layer so the burst stays crisp.
    layer = Image.new("RGBA", (r_outer * 2 + 20, 60), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    try:
        tw = ld.textlength(text, font=font)
    except AttributeError:  # pragma: no cover - old Pillow
        tw = ld.textsize(text, font=font)[0]
    ld.text(((layer.width - tw) / 2, 6), text, font=font, fill=(255, 244, 220, 255))
    layer = layer.rotate(angle, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


def patch(draw: ImageDraw.ImageDraw, box, fill=(232, 214, 170, 255)) -> None:
    """Embroidered patch: stitched (dashed) border around a cloth plate."""
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=10, fill=fill, outline=INK, width=2)
    # Stitches.
    dash, gap = 7, 5
    segs = [((x0 + 8, y0 + 5), (x1 - 8, y0 + 5)),
            ((x0 + 8, y1 - 5), (x1 - 8, y1 - 5)),
            ((x0 + 5, y0 + 8), (x0 + 5, y1 - 8)),
            ((x1 - 5, y0 + 8), (x1 - 5, y1 - 8))]
    for (ax, ay), (bx, by) in segs:
        dist = math.hypot(bx - ax, by - ay)
        steps = max(1, int(dist // (dash + gap)))
        for i in range(steps):
            t0 = i / steps
            t1 = min(1.0, i / steps + dash / dist)
            draw.line([(ax + (bx - ax) * t0, ay + (by - ay) * t0),
                       (ax + (bx - ax) * t1, ay + (by - ay) * t1)],
                      fill=WAX_DARK, width=2)


# ---------------------------------------------------------------------------
# Inventory dressing: crosshatch slots, tally marks, twine tags, chalkboard
# ---------------------------------------------------------------------------
def crosshatch(draw: ImageDraw.ImageDraw, box, spacing: int = 8,
               fill=(60, 46, 30, 70)) -> None:
    """Diagonal shading clipped to a rectangle (satchel fabric)."""
    x0, y0, x1, y1 = box
    for c in range(-(y1 - y0), (x1 - x0) + (y1 - y0), spacing):
        pts = []
        # Line x - y = x0 + c crosses the four rect edges.
        for (ex0, ey0), (ex1, ey1) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
                                         ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
            denom = (ex1 - ex0) - (ey1 - ey0)
            if denom == 0:
                continue
            # Solve param: edge point + t*edge_dir satisfies x - y = x0 + c.
            t = ((x0 + c) - ex0 + ey0) / denom
            if 0 <= t <= 1:
                pts.append((ex0 + (ex1 - ex0) * t, ey0 + (ey1 - ey0) * t))
        if len(pts) >= 2:
            draw.line([pts[0], pts[1]], fill=fill, width=1)


def tally(draw: ImageDraw.ImageDraw, x: int, y: int, n: int,
          color=INK, h: int = 18, gap: int = 6) -> int:
    """Inked tally marks in groups of five. Returns width used."""
    if n <= 0:
        return 0
    if n > 20:  # Large stacks: compact notation instead of a fence.
        return 0
    cx = x
    groups, rest = divmod(n, 5)
    blocks = groups + (1 if rest else 0)
    for b in range(blocks):
        count = 5 if b < groups else rest
        base = cx + b * (4 * gap + 10)
        for i in range(min(count, 4)):
            draw.line([(base + i * gap, y), (base + i * gap, y + h)], fill=color, width=2)
        if count == 5:
            draw.line([(base - 3, y + h - 3), (base + 4 * gap - 1, y + 2)],
                      fill=color, width=2)
    return blocks * (4 * gap + 10)


def twine_tag(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font,
              color=(150, 148, 140, 255)) -> int:
    """Item tag tied with twine: dot + string + rarity plate. Returns width."""
    draw.ellipse([x, y + 4, x + 6, y + 10], fill=INK)
    try:
        tw = draw.textlength(text, font=font)
    except AttributeError:  # pragma: no cover - old Pillow
        tw = draw.textsize(text, font=font)[0]
    w = int(tw) + 16
    draw.line([(x + 6, y + 7), (x + 12, y + 7)], fill=INK_SOFT, width=1)
    draw.rounded_rectangle([x + 12, y, x + 12 + w, y + 20], radius=5,
                           fill=(247, 236, 210, 255), outline=color, width=2)
    draw.text((x + 20, y + 2), text, font=font, fill=INK)
    return 12 + w


def chalk_panel(draw: ImageDraw.ImageDraw, box, seed: int = 41) -> None:
    """Chalkboard strip with a wooden frame (cart/checkout dressing)."""
    x0, y0, x1, y1 = box
    draw.rounded_rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], radius=6, fill=WOOD)
    draw.rounded_rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], radius=6,
                           outline=WOOD_DARK, width=2)
    draw.rounded_rectangle(box, radius=4, fill=SLATE)
    rng = _rng(seed)
    for _ in range(24):  # Chalk dust.
        draw.point((rng.randint(x0 + 3, x1 - 3), rng.randint(y0 + 3, y1 - 3)),
                   fill=(220, 220, 215, 50))
    for i, (a, b) in enumerate((((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
                                ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0)))):
        wobble_line(draw, a, b, CHALK, 1, seed * 3 + i, amp=0.8)


def sketch_frame(img: Image.Image, box, avatar: Image.Image, seed: int = 51) -> None:
    """Taped portrait: off-white mat, slight tilt feel, ink frame, tape tabs."""
    x0, y0, x1, y1 = box
    draw = ImageDraw.Draw(img)
    # Mat.
    draw.rounded_rectangle([x0 - 8, y0 - 8, x1 + 8, y1 + 8], radius=4,
                           fill=(246, 240, 222, 255))
    ava = avatar.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    img.paste(ava, (x0, y0), ava if ava.mode == "RGBA" else None)
    for i, (a, b) in enumerate((((x0 - 8, y0 - 8), (x1 + 8, y0 - 8)),
                                ((x1 + 8, y0 - 8), (x1 + 8, y1 + 8)),
                                ((x1 + 8, y1 + 8), (x0 - 8, y1 + 8)),
                                ((x0 - 8, y1 + 8), (x0 - 8, y0 - 8)))):
        wobble_line(draw, a, b, INK, 2, seed + i, amp=1.3)
    # Tape tabs on the top corners.
    for tx in (x0 - 4, x1 - 26):
        draw.polygon([(tx, y0 - 14), (tx + 30, y0 - 10),
                      (tx + 28, y0 + 6), (tx + 2, y0 + 2)],
                     fill=(235, 220, 180, 200), outline=INK_SOFT)
