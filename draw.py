#!/usr/bin/env python3
"""
THE WORLD IN A DAY -- build-time drawing program (news-image-20261119).

Paints the one-page broadsheet that sums up the world news of
Thursday 19 November 2026. Build time only: it needs Pillow and the
Noto fonts, runs on the builder's machine, and writes entry.png next
to this file. The competition server never runs it -- the submitted
main.py is a stdlib-only copier that ships the finished PNG to the
output path. Regenerate with:

    python3 draw.py   # writes entry.png next to this file

Deterministic by construction: fixed geometry, no randomness, no
clock, no network, so two runs give a byte-identical PNG.

Layout follows the winner pattern of the sibling editions: a navy
masthead with the date set huge, a field-taxonomy strip and a UTC
timeline, three large illustrated panels, eight numbered mini
panels, a dot-matrix world map with numbered pins, a stats strip,
and a numbered "ALSO ON THURSDAY" list -- 44 stories in all, each
first reported on Thursday 19 November 2026. The researched story
list, with per-story verification notes and the date-check
exclusions, lives in STORIES.md.
"""

import math
import os

from PIL import Image
from PIL import ImageDraw, ImageFont

PAGE = 1024
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")

NOTO = "/usr/share/fonts/truetype/noto"
SERIF = os.path.join(NOTO, "NotoSerif-Regular.ttf")
SERIF_B = os.path.join(NOTO, "NotoSerif-Bold.ttf")
SERIF_BLK = os.path.join(NOTO, "NotoSerif-Black.ttf")
SERIF_I = os.path.join(NOTO, "NotoSerif-Italic.ttf")
SANS = os.path.join(NOTO, "NotoSans-Regular.ttf")
SANS_B = os.path.join(NOTO, "NotoSans-Bold.ttf")
SANS_I = os.path.join(NOTO, "NotoSans-Italic.ttf")


def _hex(code):
    return (int(code[0:2], 16), int(code[2:4], 16), int(code[4:6], 16))


PAPER = _hex("f6f1e5")
PANEL_BG = _hex("fdfaf1")
INK = _hex("1c2126")
NAVY = _hex("152a42")
NAVY2 = _hex("22405f")
GOLD = _hex("b98a1c")
GOLD_L = _hex("e3b341")
RED = _hex("b21818")
GREY = _hex("5c6066")
RULE = _hex("a2987e")
CREAM = _hex("efe7d2")
MAP_BG = _hex("e3e9ec")
MAP_DOT = _hex("64809c")

REGION = {
    "europe": _hex("2563b3"),
    "mideast": _hex("bc5f16"),
    "asia": _hex("7d3c98"),
    "africa": _hex("1e8449"),
    "americas": _hex("b03a4b"),
    "oceania": _hex("148f7a"),
    "global": _hex("5d6d7e"),
}

TAG_STYLE = {
    "CONFIRMED": (NAVY, _hex("ffffff")),
    "CLAIM": (RED, _hex("ffffff")),
    "FORECAST": (GOLD, _hex("ffffff")),
}

EDGE = 14
SPAN = PAGE - 2 * EDGE

_font_cache = {}


def F(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def tw(cnv, text, font):
    return cnv.textlength(text, font=font)


def wrap(cnv, text, font, width):
    """Greedy word wrap; returns a list of lines fitting `width`."""
    lines, cur = [], ""
    for word in text.split():
        trial = word if not cur else cur + " " + word
        if tw(cnv, trial, font) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_font(cnv, text, path, width, max_lines, start, minimum):
    """Largest size from `start` down whose wrap fits `max_lines`."""
    size = start
    while size > minimum:
        font = F(path, size)
        if len(wrap(cnv, text, font, width)) <= max_lines:
            return font
        size -= 1
    return F(path, minimum)


def put(cnv, x, y, text, font, fill=INK, anchor="la"):
    cnv.text((x, y), text, font=font, fill=fill, anchor=anchor)


def spaced(cnv, x, y, text, font, fill, tracking=2):
    """Draw text with extra letter tracking (broadsheet kickers)."""
    cx = x
    for ch in text:
        cnv.text((cx, y), ch, font=font, fill=fill, anchor="la")
        cx += tw(cnv, ch, font) + tracking
    return cx - tracking


def put_r(cnv, x, y, text, font, fill=INK):
    cnv.text((x, y), text, font=font, fill=fill, anchor="ra")


def paint_lines(cnv, x, y, lines, font, leading, fill=INK):
    for line in lines:
        cnv.text((x, y), line, font=font, fill=fill, anchor="la")
        y += leading
    return y


def num_chip(cnv, cx, cy, num, size, fill, txt_fill):
    """Rounded square with a bold number centred on (cx, cy)."""
    r = size // 2
    cnv.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=3,
                          fill=fill)
    put(cnv, cx, cy + 1, str(num), F(SANS_B, size - 5), fill=txt_fill,
        anchor="mm")


def disc(cnv, cx, cy, rad, num, fill, halo=1):
    cnv.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=fill,
                outline=_hex("ffffff"), width=halo)
    put(cnv, cx, cy + 1, str(num), F(SANS_B, rad + 2), fill=_hex("ffffff"),
        anchor="mm")


def tag_chip(cnv, x_right, cy, tag):
    bg, fg = TAG_STYLE[tag]
    font = F(SANS_B, 8)
    w = tw(cnv, tag, font) + 10
    cnv.rounded_rectangle([x_right - w, cy - 7, x_right, cy + 7], radius=2,
                          fill=bg)
    put(cnv, x_right - w / 2, cy + 1, tag, font, fill=fg, anchor="mm")
    return w


# ---------------------------------------------------------------------------
# Scene painters. Each paints inside box=(x0, y0, x1, y1) with flat
# shapes and a limited palette, and bakes in one data callout chip.
# ---------------------------------------------------------------------------

def callout(cnv, x0, y1, text):
    font = F(SANS_B, 9)
    w = tw(cnv, text, font) + 12
    cnv.rectangle([x0, y1 - 15, x0 + w, y1], fill=NAVY)
    put(cnv, x0 + 6, y1 - 7, text, font, fill=_hex("ffffff"), anchor="lm")


def scene_gta(cnv, box):
    x0, y0, x1, y1 = box
    bands = ["2b2350", "5b2a5e", "a03a56", "d96a3f", "eda83e"]
    bh = (y1 - y0) * 2 // 3
    for i, code in enumerate(bands):
        cnv.rectangle([x0, y0 + bh * i // 5, x1, y0 + bh * (i + 1) // 5],
                      fill=_hex(code))
    # skyline silhouette
    base = y0 + bh
    towers = [(0.02, 0.52), (0.10, 0.78), (0.19, 0.60), (0.27, 0.88),
              (0.38, 0.66), (0.47, 0.95), (0.58, 0.70), (0.66, 0.84),
              (0.76, 0.58), (0.84, 0.76), (0.93, 0.55)]
    for fx, fh in towers:
        tx = x0 + fx * (x1 - x0)
        twd = (x1 - x0) * 0.055
        cnv.rectangle([tx, base - fh * bh, tx + twd, base],
                      fill=_hex("171226"))
        for wy in range(int(base - fh * bh) + 4, base - 4, 7):
            for wx in range(int(tx) + 3, int(tx + twd) - 3, 6):
                if (wx * 7 + wy * 13) % 5 == 0:
                    cnv.rectangle([wx, wy, wx + 2, wy + 3],
                                  fill=_hex("f5c531"))
    # palms
    for fx in (0.30, 0.70):
        px, py = x0 + fx * (x1 - x0), base
        cnv.line([px, py, px + 3, py - bh * 0.42], fill=_hex("120e20"),
                 width=3)
        for ang in (-160, -120, -80, -40, -5):
            ex = px + 3 + 13 * math.cos(math.radians(ang))
            ey = py - bh * 0.42 + 8 * math.sin(math.radians(ang))
            cnv.arc([px - 10, py - bh * 0.42 - 6, px + 16,
                     py - bh * 0.42 + 8], start=ang, end=ang + 40,
                    fill=_hex("120e20"), width=2)
    # road with light streaks
    cnv.rectangle([x0, base, x1, y1], fill=_hex("100d18"))
    mid = (x0 + x1) // 2
    for i, fx in enumerate((0.08, 0.3, 0.52, 0.74, 0.92)):
        sx = x0 + fx * (x1 - x0)
        cnv.line([mid + (sx - mid) * 0.25, y1, sx, base + 3],
                 fill=_hex("3a3550"), width=2)
    cnv.line([x0 + 6, base + 8, x1 - 40, base + 8], fill=_hex("ff5f45"),
             width=2)
    cnv.line([x0 + 50, base + 13, x1 - 6, base + 13], fill=_hex("ffd76a"),
             width=2)
    callout(cnv, x0, y1, "13 YEARS ON · $79.99")


def scene_summit(cnv, box):
    x0, y0, x1, y1 = box
    cnv.rectangle(box, fill=_hex("b9cdd9"))
    cnv.rectangle([x0, y1 - 12, x1, y1], fill=_hex("8fa9ba"))
    # Shenzhen towers behind
    for fx, fh in ((0.55, 0.55), (0.64, 0.8), (0.74, 0.62), (0.83, 0.72),
                   (0.92, 0.5)):
        tx = x0 + fx * (x1 - x0)
        cnv.rectangle([tx, y1 - 12 - fh * (y1 - y0), tx + 12, y1 - 12],
                      fill=_hex("6e8aa0"))
    # three banners on poles
    flags = [("us",), ("cn",), ("ru",)]
    bw = (x1 - x0) * 0.15
    bh = (y1 - y0) * 0.52
    for i, (kind,) in enumerate(flags):
        fx = x0 + (x1 - x0) * (0.06 + i * 0.17)
        fy = y0 + 8
        cnv.line([fx, fy - 3, fx, y1 - 12], fill=_hex("3c4652"), width=2)
        if kind == "us":
            cnv.rectangle([fx + 2, fy, fx + 2 + bw, fy + bh],
                          fill=_hex("ffffff"))
            for s in range(4):
                cnv.rectangle([fx + 2, fy + s * bh / 4, fx + 2 + bw,
                               fy + (s + 0.5) * bh / 4], fill=RED)
            cnv.rectangle([fx + 2, fy, fx + 2 + bw * 0.45, fy + bh * 0.5],
                          fill=NAVY)
        elif kind == "cn":
            cnv.rectangle([fx + 2, fy, fx + 2 + bw, fy + bh], fill=RED)
            for dx, dy, r in ((7, 7, 3), (15, 4, 1), (17, 9, 1),
                              (17, 14, 1), (15, 18, 1)):
                cnv.ellipse([fx + 2 + dx - r, fy + dy - r, fx + 2 + dx + r,
                             fy + dy + r], fill=GOLD_L)
        else:
            third = bh / 3
            cnv.rectangle([fx + 2, fy, fx + 2 + bw, fy + third],
                          fill=_hex("ffffff"))
            cnv.rectangle([fx + 2, fy + third, fx + 2 + bw, fy + 2 * third],
                          fill=_hex("2c4f9e"))
            cnv.rectangle([fx + 2, fy + 2 * third, fx + 2 + bw, fy + bh],
                          fill=RED)
    put(cnv, x0 + (x1 - x0) * 0.60, y0 + 14, "KYLIN VILLA",
        F(SANS_B, 10), fill=NAVY)
    put(cnv, x0 + (x1 - x0) * 0.60, y0 + 28, "SHENZHEN",
        F(SANS_B, 10), fill=NAVY)
    callout(cnv, x0, y1, "FIRST TRILATERAL")


def scene_ipo(cnv, box):
    x0, y0, x1, y1 = box
    cnv.rectangle(box, fill=NAVY)
    # ascending step chart
    pts = [(0.05, 0.78), (0.22, 0.78), (0.22, 0.60), (0.40, 0.60),
           (0.40, 0.44), (0.58, 0.44), (0.58, 0.28), (0.74, 0.28)]
    xy = [(x0 + fx * (x1 - x0), y0 + fy * (y1 - y0)) for fx, fy in pts]
    cnv.line(xy, fill=GOLD_L, width=3)
    ex, ey = xy[-1]
    cnv.polygon([(ex, ey), (ex - 10, ey - 1), (ex - 3, ey + 8)],
                fill=GOLD_L)
    for gx in (0.22, 0.40, 0.58):
        gx0 = x0 + gx * (x1 - x0)
        cnv.line([gx0, y0 + 6, gx0, y1 - 16], fill=NAVY2, width=1)
    put(cnv, x0 + (x1 - x0) * 0.78, y0 + 10, "ANT", F(SERIF_BLK, 30),
        fill=_hex("ffffff"))
    put(cnv, x0 + (x1 - x0) * 0.78, y0 + 44, "NASDAQ · DAY ONE",
        F(SANS_B, 9), fill=GOLD_L)
    callout(cnv, x0, y1, "$83 A SHARE · $81.3BN")


def scene_bridge(cnv, box):
    x0, y0, x1, y1 = box
    cnv.rectangle(box, fill=_hex("cfdde8"))
    sea_y = y0 + (y1 - y0) * 0.62
    cnv.rectangle([x0, sea_y, x1, y1], fill=_hex("4a7396"))
    for i in range(5):
        wy = sea_y + 5 + i * 6
        cnv.line([x0 + 8 + (i % 3) * 22, wy, x0 + 60 + (i % 3) * 22, wy],
                 fill=_hex("6d93b3"), width=1)
    deck_y = y0 + (y1 - y0) * 0.40
    gap = (x1 - x0) * 0.14
    mid = (x0 + x1) // 2
    cnv.line([x0 + 4, deck_y + 6, mid - gap / 2, deck_y], fill=_hex("37424e"),
             width=4)
    cnv.line([mid + gap / 2, deck_y, x1 - 4, deck_y + 6],
             fill=_hex("37424e"), width=4)
    cnv.line([mid - gap / 2, deck_y, mid - gap * 0.1, deck_y + 12],
             fill=_hex("37424e"), width=3)
    for fx in (0.16, 0.34, 0.66, 0.84):
        px = x0 + fx * (x1 - x0)
        cnv.line([px, deck_y + 4, px, sea_y], fill=_hex("37424e"), width=3)
    # burst at the gap
    for ang in range(0, 360, 30):
        r1, r2 = 3, 10 if ang % 60 == 0 else 7
        cnv.line([mid + r1 * math.cos(math.radians(ang)),
                  deck_y - 4 + r1 * math.sin(math.radians(ang)),
                  mid + r2 * math.cos(math.radians(ang)),
                  deck_y - 4 + r2 * math.sin(math.radians(ang))],
                 fill=RED, width=2)
    cnv.ellipse([mid - 3, deck_y - 7, mid + 3, deck_y - 1], fill=RED)
    callout(cnv, x0, y1, "3RD STRIKE THIS WEEK")


def scene_icj(cnv, box):
    x0, y0, x1, y1 = box
    cnv.rectangle(box, fill=_hex("e7dfc9"))
    w = x1 - x0
    h = y1 - y0
    cx = x0 + w * 0.34
    top = y0 + h * 0.14
    cnv.polygon([(cx - w * 0.26, top + h * 0.18), (cx + w * 0.26, top + h * 0.18),
                 (cx, top)], fill=NAVY)
    cnv.rectangle([cx - w * 0.28, top + h * 0.20, cx + w * 0.28,
                   top + h * 0.26], fill=NAVY)
    for i in range(5):
        cxx = cx - w * 0.22 + i * w * 0.11
        cnv.rectangle([cxx, top + h * 0.28, cxx + w * 0.05, top + h * 0.72],
                      fill=_hex("fbf7ea"), outline=NAVY, width=1)
    cnv.rectangle([cx - w * 0.28, top + h * 0.74, cx + w * 0.28,
                   top + h * 0.80], fill=NAVY)
    cnv.rectangle([cx - w * 0.32, top + h * 0.82, cx + w * 0.32, y1],
                  fill=_hex("cbbd97"))
    # scales of justice on the right
    sx = x0 + w * 0.80
    sy = y0 + h * 0.22
    cnv.line([sx, sy, sx, y1 - 16], fill=INK, width=2)
    cnv.line([sx - 16, sy + 5, sx + 16, sy + 5], fill=INK, width=2)
    for sgn in (-1, 1):
        px = sx + sgn * 16
        cnv.line([px, sy + 5, px - 6, sy + 17], fill=INK, width=1)
        cnv.line([px, sy + 5, px + 6, sy + 17], fill=INK, width=1)
        cnv.arc([px - 8, sy + 12, px + 8, sy + 24], start=0, end=180,
                fill=GOLD, width=2)
    cnv.rectangle([sx - 9, y1 - 16, sx + 9, y1 - 13], fill=INK)
    callout(cnv, x0, y1, "FILED 2019 · THE HAGUE")


def scene_cyclone(cnv, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cnv.rectangle(box, fill=_hex("7fa3bd"))
    # land mass bottom-left with a curved coast
    coast = [(x0, y1), (x0, y0 + h * 0.30), (x0 + w * 0.16, y0 + h * 0.44),
             (x0 + w * 0.26, y0 + h * 0.62), (x0 + w * 0.40, y0 + h * 0.78),
             (x0 + w * 0.52, y1)]
    cnv.polygon(coast, fill=_hex("e5d29a"))
    cnv.line(coast[1:], fill=_hex("b89b57"), width=2)
    put(cnv, x0 + 8, y0 + h * 0.36, "ODISHA", F(SANS_B, 9), fill=_hex("7a6428"))
    # cyclone spiral over the sea
    cx, cy = x0 + w * 0.72, y0 + h * 0.46
    for rad, start in ((26, 20), (19, 150), (12, 280)):
        cnv.arc([cx - rad, cy - rad * 0.72, cx + rad, cy + rad * 0.72],
                start=start, end=start + 235, fill=_hex("ffffff"), width=3)
    cnv.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=NAVY)
    # rain streaks
    for i in range(7):
        rx = x0 + w * (0.55 + 0.06 * i)
        cnv.line([rx, y0 + h * 0.78, rx - 5, y0 + h * 0.92],
                 fill=_hex("d7e6f0"), width=2)
    # dashed forecast track toward the coast
    for t in (0.25, 0.5, 0.75):
        px = cx + (x0 + w * 0.34 - cx) * t
        py = cy + (y0 + h * 0.66 - cy) * t
        cnv.ellipse([px - 2, py - 2, px + 2, py + 2], fill=RED)
    callout(cnv, x0, y1, "LANDFALL FRI · NOON")


def scene_children(cnv, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cnv.rectangle(box, fill=_hex("efe9da"))
    # rising bars behind
    for i, fh in enumerate((0.30, 0.42, 0.55, 0.72)):
        bx = x0 + w * (0.55 + i * 0.11)
        cnv.rectangle([bx, y1 - 14 - fh * h, bx + w * 0.08, y1 - 14],
                      fill=_hex("c8bfa8") if i < 3 else RED)
    put(cnv, x0 + 8, y0 + 5, "2015 → 2025", F(SANS_B, 8), fill=GREY)
    # four child figures; the fourth stands in a red zone band
    cnv.rectangle([x0 + w * 0.40, y0, x0 + w * 0.52, y1], fill=_hex("e8c9c2"))
    for i in range(4):
        fx = x0 + w * (0.07 + i * 0.115)
        fy = y1 - 14
        col = _hex("33475e")
        cnv.ellipse([fx - 5, fy - 30, fx + 5, fy - 20], fill=col)
        cnv.line([fx, fy - 20, fx, fy - 8], fill=col, width=3)
        cnv.line([fx, fy - 8, fx - 5, fy], fill=col, width=2)
        cnv.line([fx, fy - 8, fx + 5, fy], fill=col, width=2)
        cnv.line([fx, fy - 17, fx - 6, fy - 11], fill=col, width=2)
        cnv.line([fx, fy - 17, fx + 6, fy - 11], fill=col, width=2)
    callout(cnv, x0, y1, "589M CHILDREN · 23.4%")


def scene_cop(cnv, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cnv.rectangle(box, fill=_hex("dcebe4"))
    cx, cy, r = x0 + w * 0.30, y0 + h * 0.48, h * 0.34
    cnv.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_hex("7fb2d9"),
                outline=NAVY, width=1)
    cnv.pieslice([cx - r, cy - r, cx + r, cy + r], start=90, end=215,
                 fill=_hex("58a05c"))
    cnv.pieslice([cx - r, cy - r, cx + r, cy + r], start=300, end=60,
                 fill=_hex("58a05c"))
    cnv.arc([cx - r * 0.45, cy - r, cx + r * 0.45, cy + r], start=0, end=360,
            fill=NAVY, width=1)
    cnv.line([cx - r, cy, cx + r, cy], fill=NAVY, width=1)
    # two rival text blocks, split by a jagged line
    bx = x0 + w * 0.55
    cnv.rectangle([bx, y0 + 8, bx + w * 0.19, y0 + h * 0.52],
                  fill=_hex("fbf7ea"), outline=INK, width=1)
    cnv.rectangle([bx + w * 0.23, y0 + 8, bx + w * 0.42, y0 + h * 0.52],
                  fill=_hex("fbf7ea"), outline=INK, width=1)
    for i in range(3):
        cnv.line([bx + 4, y0 + 15 + i * 7, bx + w * 0.19 - 4,
                  y0 + 15 + i * 7], fill=GREY, width=2)
        cnv.line([bx + w * 0.23 + 4, y0 + 15 + i * 7, bx + w * 0.42 - 4,
                  y0 + 15 + i * 7], fill=GREY, width=2)
    cnv.line([bx + w * 0.21, y0 + 6, bx + w * 0.20, y0 + h * 0.34],
             fill=RED, width=2)
    cnv.line([bx + w * 0.20, y0 + h * 0.34, bx + w * 0.22, y0 + h * 0.54],
             fill=RED, width=2)
    put(cnv, bx, y0 + h * 0.60, "2 RIVAL CLAUSES", F(SANS_B, 9), fill=RED)
    callout(cnv, x0, y1, "CLOSES FRIDAY")


def scene_cricket(cnv, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cnv.rectangle(box, fill=_hex("79a85b"))
    cnv.rectangle([x0, y0 + h * 0.30, x1, y0 + h * 0.34], fill=_hex("8fb873"))
    # pitch
    px0, px1 = x0 + w * 0.16, x1 - w * 0.16
    py = y0 + h * 0.60
    cnv.rectangle([px0, py - 8, px1, py + 10], fill=_hex("e3d3a1"))
    cnv.line([px0, py - 8, px1, py - 8], fill=_hex("c9b678"), width=1)
    for fx in (px0 + 8, px1 - 8):
        for s in (-4, 0, 4):
            cnv.line([fx + s, py - 6, fx + s, py + 6], fill=_hex("f3ecd7"),
                     width=2)
        cnv.line([fx - 4, py - 6, fx + 4, py - 6], fill=_hex("d94f3d"),
                 width=2)
    # ball arc
    for t in (0.15, 0.35, 0.55, 0.75):
        bx = px0 + (px1 - px0) * t
        by = py - 10 - 16 * math.sin(math.pi * t)
        cnv.ellipse([bx - 1.5, by - 1.5, bx + 1.5, by + 1.5],
                    fill=_hex("a52a21"))
    cnv.ellipse([px1 - 14, py - 24, px1 - 8, py - 18], fill=_hex("a52a21"))
    put(cnv, x0 + w * 0.60, y0 + 6, "BASIN RESERVE", F(SANS_B, 9),
        fill=_hex("ffffff"))
    callout(cnv, x0, y1, "DAY ONE · 1ST TEST")


def scene_apec(cnv, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cnv.rectangle(box, fill=_hex("bcd2de"))
    cnv.rectangle([x0, y0 + h * 0.66, x1, y1], fill=_hex("5d87a3"))
    # three sails (Shenzhen bay)
    for fx, fh, col in ((0.16, 0.5, "fbf7ea"), (0.30, 0.62, "e8eef2"),
                        (0.46, 0.44, "fbf7ea")):
        sx = x0 + w * fx
        sy = y0 + h * 0.66
        cnv.polygon([(sx, sy), (sx, sy - fh * h), (sx + w * 0.09, sy)],
                    fill=_hex(col), outline=_hex("46657c"))
        cnv.line([sx - 3, sy, sx + w * 0.11, sy], fill=_hex("37424e"),
                 width=2)
    # ring of 21 member dots
    cx, cy = x0 + w * 0.70, y0 + h * 0.32
    for i in range(21):
        ang = 2 * math.pi * i / 21
        dx, dy = cx + 15 * math.cos(ang), cy + 10 * math.sin(ang)
        cnv.ellipse([dx - 2, dy - 2, dx + 2, dy + 2], fill=GOLD)
    put(cnv, cx, cy + 1, "21", F(SANS_B, 11), fill=NAVY, anchor="mm")
    put(cnv, cx, cy + 15, "ECONOMIES", F(SANS_B, 7), fill=NAVY, anchor="mm")
    callout(cnv, x0, y1, "$20M FOR APEC")


def scene_twotwo(cnv, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cnv.rectangle(box, fill=_hex("e9e2cf"))
    fw, fh = w * 0.30, h * 0.60
    # India
    fx, fy = x0 + w * 0.07, y0 + h * 0.13
    cnv.line([fx, fy - 4, fx, y1 - 12], fill=_hex("3c4652"), width=2)
    third = fh / 3
    cnv.rectangle([fx + 2, fy, fx + 2 + fw, fy + third], fill=_hex("e08a3c"))
    cnv.rectangle([fx + 2, fy + third, fx + 2 + fw, fy + 2 * third],
                  fill=_hex("fbf7ea"))
    cnv.rectangle([fx + 2, fy + 2 * third, fx + 2 + fw, fy + fh],
                  fill=_hex("2e7d46"))
    cnv.ellipse([fx + 2 + fw / 2 - 5, fy + third + third / 2 - 5,
                 fx + 2 + fw / 2 + 5, fy + third + third / 2 + 5],
                outline=NAVY, width=2)
    # Japan
    fx2 = x0 + w * 0.60
    cnv.line([fx2, fy - 4, fx2, y1 - 12], fill=_hex("3c4652"), width=2)
    cnv.rectangle([fx2 + 2, fy, fx2 + 2 + fw, fy + fh], fill=_hex("fbf7ea"),
                  outline=_hex("8a8272"), width=1)
    cnv.ellipse([fx2 + 2 + fw / 2 - 8, fy + fh / 2 - 8,
                 fx2 + 2 + fw / 2 + 8, fy + fh / 2 + 8], fill=RED)
    put(cnv, x0 + w * 0.465, y0 + h * 0.40, "2+2", F(SERIF_BLK, 17),
        fill=NAVY, anchor="mm")
    callout(cnv, x0, y1, "2+2 DIALOGUE")


# ---------------------------------------------------------------------------
# Dot-matrix world map. Coastline polygons (lon/lat outlines, the house
# data set from the sibling editions) are rasterised into a dot grid by
# point-in-polygon tests; numbered pins mark panels 1-10.
# ---------------------------------------------------------------------------

def _parse_poly(raw):
    pts = []
    for pair in raw.split(";"):
        lon_s, lat_s = pair.split(",")
        pts.append((int(lon_s), int(lat_s)))
    return pts


NAM_RAW = "-168,65;-158,71;-140,70;-130,71;-120,71;-110,68;-100,69;-95,69;-90,69;-85,66;-82,66;-79,62;-76,60;-70,62;-65,60;-60,55;-55,52;-56,50;-60,46;-65,44;-68,44;-70,42;-74,39;-76,35;-79,33;-80,31;-80,27;-81,25;-82,27;-84,29;-87,30;-89,29;-94,29;-97,28;-97,25;-97,22;-94,17;-90,14;-87,13;-83,9;-79,9;-81,12;-85,15;-90,14;-94,16;-97,16;-102,19;-105,23;-108,25;-111,29;-114,31;-117,33;-120,34;-122,37;-123,40;-124,45;-124,48;-128,52;-132,55;-137,58;-145,60;-152,59;-156,58;-161,59;-165,60;-168,63"
GREENLAND_RAW = "-46,59;-40,63;-32,68;-22,70;-20,73;-25,78;-32,80;-45,80;-55,78;-58,75;-57,70;-55,65;-53,61"
SAM_RAW = "-78,7;-75,10;-72,12;-68,11;-64,10;-61,9;-57,7;-54,6;-51,4;-50,1;-46,-1;-42,-3;-38,-5;-35,-8;-36,-10;-38,-13;-39,-18;-40,-21;-42,-23;-45,-24;-48,-26;-50,-29;-52,-32;-54,-34;-57,-37;-58,-39;-61,-39;-62,-41;-63,-43;-65,-45;-66,-47;-67,-49;-68,-51;-68,-53;-70,-54;-72,-54;-73,-51;-74,-48;-74,-44;-73,-40;-73,-36;-72,-31;-71,-27;-70,-22;-70,-18;-72,-16;-75,-14;-77,-11;-79,-8;-80,-5;-81,-3;-80,0;-79,2;-78,4"
EUROPE_RAW = "-9,37;-9,43;-8,44;-4,44;-1,45;-2,47;-4,48;-1,50;1,51;3,52;5,53;7,54;8,55;7,57;8,58;10,59;7,59;5,60;5,62;8,63;11,65;14,67;17,69;21,70;26,71;31,71;38,69;44,68;48,66;50,64;48,62;44,60;42,58;40,56;38,55;35,55;33,54;31,52;30,51;28,50;27,48;29,46;28,45;29,43;28,41;27,40;26,39;27,38;26,37;24,37;23,36;22,37;21,38;20,39;19,40;16,39;15,38;12,38;13,41;12,43;10,44;7,44;3,43;0,40;-1,38;-2,37"
ITALY_RAW = "8,44;10,44;11,43;13,41;14,40;16,38;18,40;16,40;14,41;12,42;10,43;8,44"
UK_RAW = "-5,50;-3,50;-2,52;-3,55;-4,57;-3,58;-4,59;-6,58;-8,55;-6,54;-5,52"
IRELAND_RAW = "-10,52;-8,52;-6,52;-6,54;-8,55;-10,54"
AFRICA_RAW = "-6,35;-2,35;3,37;9,37;11,34;15,32;20,32;25,32;30,31;32,31;33,28;35,24;37,22;39,20;40,18;42,15;43,12;45,11;48,11;51,11;48,9;46,6;43,3;41,-1;40,-5;40,-9;39,-13;38,-17;37,-20;36,-23;35,-26;33,-28;31,-30;29,-32;27,-34;25,-34;22,-35;20,-35;19,-33;18,-31;17,-28;16,-24;15,-21;14,-18;13,-14;12,-11;11,-7;10,-4;9,-1;9,2;8,4;6,4;3,6;-1,5;-4,5;-7,4;-9,4;-12,7;-14,9;-16,12;-17,15;-17,18;-16,21;-16,24;-15,27;-14,29;-11,31;-8,33"
MADAGASCAR_RAW = "44,-12;47,-13;49,-15;50,-17;48,-20;46,-23;45,-25;44,-23;43,-20;43,-16"
ASIA_RAW = "26,41;28,41;30,42;31,44;30,46;31,48;30,50;32,52;34,54;36,55;39,55;42,57;44,59;46,62;48,64;50,66;55,68;62,69;68,70;73,71;78,72;84,73;90,74;96,76;102,77;108,77;113,74;118,73;124,72;130,71;136,71;142,72;148,71;154,70;160,69;166,67;172,66;178,65;173,62;168,61;163,60;159,57;157,53;156,51;153,49;150,46;145,45;142,43;141,41;139,39;137,36;134,35;131,34;129,33;126,31;123,30;121,28;120,26;119,24;116,23;112,22;109,20;108,17;107,14;106,10;104,7;102,6;100,7;99,10;98,13;97,15;95,16;93,17;91,16;90,19;89,21;88,22;86,20;84,19;82,16;80,14;78,9;77,8;76,10;75,13;73,16;72,19;70,21;68,23;66,25;63,25;60,25;57,26;55,25;53,26;51,28;50,29;49,30;48,29;50,27;52,25;54,24;56,24;58,23;59,22;57,21;55,20;53,18;51,16;49,14;47,13;45,12;43,13;42,15;41,17;40,20;39,22;37,24;35,28;34,31;34,34;36,36;35,37;33,36;31,36;29,36;27,37;26,38"
JAPAN_RAW = "140,36;141,38;141,40;142,42;143,43;142,45;141,44;140,41;139,38;138,36"
JAPAN2_RAW = "131,32;132,33;134,34;135,35;133,34;131,33"
BORNEO_RAW = "109,1;113,3;117,5;119,2;118,-1;115,-3;111,-3;109,-1"
SUMATRA_RAW = "95,5;99,3;103,-1;105,-4;106,-6;103,-4;99,0;96,3"
JAVA_RAW = "106,-6;110,-7;113,-7;114,-8;110,-8;106,-7"
SULAWESI_RAW = "119,0;121,1;123,0;121,-2;120,-4;119,-2"
NEWGUINEA_RAW = "131,-1;136,-2;141,-3;146,-4;149,-6;150,-8;147,-9;143,-7;138,-5;133,-3"
PHILIPPINES_RAW = "120,18;121,16;122,14;121,13;120,14;120,16"
AUSTRALIA_RAW = "113,-22;112,-25;114,-29;115,-32;115,-34;117,-35;120,-34;124,-33;127,-32;130,-32;132,-32;134,-33;135,-35;137,-36;139,-37;140,-38;143,-38;145,-38;147,-39;149,-38;150,-37;151,-34;153,-31;153,-28;153,-25;152,-23;150,-21;148,-19;146,-18;144,-15;143,-13;142,-11;141,-15;141,-17;140,-19;139,-18;137,-16;136,-15;135,-12;132,-11;130,-12;128,-13;126,-14;124,-16;122,-17;120,-19;118,-20;116,-21"
NZ_RAW = "167,-45;169,-44;171,-43;172,-42;173,-40;174,-39;175,-37;176,-38;175,-40;173,-41;171,-42;169,-44;167,-46"

CONTINENTS = [_parse_poly(raw) for raw in (
    NAM_RAW, GREENLAND_RAW, SAM_RAW, EUROPE_RAW, ITALY_RAW, UK_RAW,
    IRELAND_RAW, AFRICA_RAW, MADAGASCAR_RAW, ASIA_RAW, JAPAN_RAW,
    JAPAN2_RAW, BORNEO_RAW, SUMATRA_RAW, JAVA_RAW, SULAWESI_RAW,
    NEWGUINEA_RAW, PHILIPPINES_RAW, AUSTRALIA_RAW, NZ_RAW)]


def _inside(lon, lat, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            xin = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if lon < xin:
                inside = not inside
    return inside


# (number, lon, lat, dx, dy, region)
PINS = [
    (1, -81, 27, 0, 0, "global"),
    (2, 114, 23, -5, -5, "asia"),
    (3, -74, 41, 0, 0, "americas"),
    (4, 37, 45, 2, -2, "europe"),
    (5, 4, 52, -3, 0, "global"),
    (6, 86, 20, 0, 0, "asia"),
    (7, 36, 31, 5, 3, "global"),
    (8, 31, 37, -5, -3, "global"),
    (9, 175, -41, 0, 0, "oceania"),
    (10, 114, 23, 12, 8, "asia"),
]


def paint_map(cnv, box):
    x0, y0, x1, y1 = box
    cnv.rectangle(box, fill=MAP_BG)
    w, h = x1 - x0, y1 - y0

    def project(lon, lat):
        return (x0 + (lon + 168) / 360.0 * w, y0 + (84 - lat) / 144.0 * h)

    lat = 82.5
    while lat > -58:
        lon = -166.5
        while lon < 190:
            for poly in CONTINENTS:
                if _inside(lon, lat, poly):
                    px, py = project(lon, lat)
                    cnv.ellipse([px - 1.6, py - 1.6, px + 1.6, py + 1.6],
                                fill=MAP_DOT)
                    break
            lon += 3.0
        lat -= 3.0
    for num, lon, lat_, dx, dy, region in PINS:
        px, py = project(lon, lat_)
        disc(cnv, px + dx, py + dy, 9, num, REGION[region], halo=2)
    cnv.rectangle(box, outline=RULE, width=1)


# ---------------------------------------------------------------------------
# Page content. Panels: (number, region, field, kicker, source, tag,
# scene, headline, deck). Also: (number, region, field, text).
# ---------------------------------------------------------------------------

FIELD_LABEL = {
    "diplomacy": "DIPLOMACY",
    "war": "WAR & SECURITY",
    "business": "BUSINESS & TECH",
    "climate": "CLIMATE & WEATHER",
    "politics": "POLITICS & COURTS",
    "science": "HEALTH & SCIENCE",
    "culture": "CULTURE & SPORT",
    "society": "SOCIETY",
}
FIELD_COLOR = {
    "diplomacy": _hex("2563b3"),
    "war": _hex("b21818"),
    "business": _hex("1e8449"),
    "climate": _hex("148f7a"),
    "politics": _hex("7d3c98"),
    "science": _hex("bc5f16"),
    "culture": _hex("b03a4b"),
    "society": _hex("5d6d7e"),
}

TOP = [
    (1, "global", "culture", "GLOBAL · GAMES", "BBC", "CONFIRMED",
     scene_gta, "GTA VI is out: the world enters Vice City",
     "Thirteen years after GTA V, Rockstar's crime epic unlocks time "
     "zone by time zone — the Americas and Europe get in on Thursday."),
    (2, "asia", "diplomacy", "ASIA · DIPLOMACY", "REUTERS · NYT",
     "CONFIRMED", scene_summit,
     "Trump, Xi and Putin hold first trilateral talks",
     "One hour at Shenzhen's Kylin Villa, on the APEC sidelines: "
     "nuclear arms, Ukraine and Iran — and no agreement expected."),
    (3, "americas", "business", "AMERICAS · BUSINESS", "CNBC",
     "CONFIRMED", scene_ipo,
     "Anthropic opens on Nasdaq in record $81.3bn sale",
     "Priced at $83, above its range, the Claude maker's shares begin "
     "trading as ANT — the largest offering on record."),
]

MINI_A = [
    (4, "europe", "war", "EUROPE · UKRAINE WAR", "REUTERS", "CLAIM",
     scene_bridge, "Crimean Bridge hit a third time in a week",
     "A fresh overnight strike halts traffic again, Crimea's "
     "Russian-installed governor says; damage is still being assessed."),
    (5, "global", "politics", "GLOBAL · COURTS", "ICJ · BBC", "CONFIRMED",
     scene_icj, "World Court delivers Myanmar genocide verdict",
     "Seven years after The Gambia filed, judges in The Hague decide "
     "whether Myanmar committed genocide against the Rohingya."),
    (6, "asia", "climate", "ASIA · WEATHER", "IMD", "FORECAST",
     scene_cyclone, "Akvan nears Odisha: 47,000 moved to safety",
     "Schools shut in six districts as the severe cyclone closes in; "
     "landfall is due near Puri at noon on Friday, gusts to 110 km/h."),
    (7, "global", "society", "GLOBAL · SOCIETY", "RELIEFWEB", "CONFIRMED",
     scene_children, "Nearly 1 in 4 children now live in war zones",
     "A record 589 million children — 23.4% of the world's total — "
     "live in conflict zones, Save the Children finds."),
]

MINI_B = [
    (8, "global", "climate", "GLOBAL · CLIMATE", "REUTERS", "CONFIRMED",
     scene_cop, "COP31 enters final two days, still split",
     "Closing plenaries open in Antalya with two rival fossil-fuel "
     "clauses unresolved; a new draft is due and the summit ends Friday."),
    (9, "oceania", "culture", "OCEANIA · SPORT", "CRICBUZZ", "CONFIRMED",
     scene_cricket, "India open Test series in Wellington",
     "The first Test against New Zealand starts at the Basin Reserve — "
     "India's first Test tour there in six years, WTC points at stake."),
    (10, "asia", "diplomacy", "ASIA · TRADE", "XINHUA", "CONFIRMED",
     scene_apec, "Xi opens APEC summit with $20m pledge",
     "China offers $20 million for APEC projects and pushes a Free "
     "Trade Area of the Asia-Pacific; Putin backs the Shenzhen draft."),
    (11, "asia", "war", "ASIA · DEFENCE", "PTI", "CONFIRMED",
     scene_twotwo, "India and Japan hold 2+2 defence talks",
     "The two countries review defence ties and strategic cooperation, "
     "as Jaishankar says trusted partnerships matter more than ever."),
]

ALSO = [
    (12, "americas", "diplomacy", "Ottawa: Carney adjusts China ties, seeks right US deal"),
    (13, "americas", "war", "US senators warn AI cyber threats outpace defences"),
    (14, "mideast", "climate", "Saudi Arabia: danger passed in three southern cities"),
    (15, "asia", "business", "Trump tells APEC he opposes global AI regulation"),
    (16, "global", "culture", "2.4m watch GTA VI on Twitch in its first hour live"),
    (17, "americas", "culture", "US Army offers soldiers a four-day pass to play GTA VI"),
    (18, "global", "science", "Study: nearly all coral reefs threatened within 50 years"),
    (19, "asia", "society", "Three workers die at NTPC plant in Jharkhand"),
    (20, "asia", "war", "LeT commander killed in J&K encounter, army says"),
    (21, "asia", "politics", "Air India crash probe nears completion"),
    (22, "asia", "climate", "India's renewable capacity stands at 299.25 GW"),
    (23, "global", "business", "Oil falls as supply improves, stockpiles build"),
    (24, "global", "science", "Bacterial toxin linked to early-onset bowel cancer rise"),
    (25, "europe", "science", "ESA chief calls for binding space laws"),
    (26, "americas", "war", "Reports: outage hits NSA internal networks"),
    (27, "americas", "politics", "House Democrats order Trump allies to preserve records"),
    (28, "europe", "diplomacy", "EU pauses long-term UK talks over Brexit stance"),
    (29, "americas", "society", "BBC investigates new abuse claims at McDonald's"),
    (30, "mideast", "war", "USS Theodore Roosevelt arrives in the Middle East"),
    (31, "americas", "diplomacy", "US panel urges China sanctions over Panama-flagged ships"),
    (32, "asia", "politics", "Congress targets Modi govt on inflation, seeks white paper"),
    (33, "asia", "society", "Murmu: 50 crore Indians out of extreme poverty"),
    (34, "asia", "society", "Delhi-NCR schools reopen as GRAP-III curbs revoked"),
    (35, "asia", "business", "Goldman ups India to overweight; Nifty target 28,500"),
    (36, "asia", "business", "India slaps 162.5% duty on bulk Scotch imports"),
    (37, "asia", "business", "Air India Express names Rajawat CEO from 1 Dec"),
    (38, "europe", "politics", "France: minister says Mélenchon could win presidency"),
    (39, "asia", "politics", "Delhi court: charges for 14 in NEET-UG leak case"),
    (40, "asia", "culture", "Sports Ministry forms 14-member league committee"),
    (41, "americas", "business", "Tech outages no coincidence, AI aids attacks: Arora"),
    (42, "asia", "business", "Tata Steel CEO: Chinese imports still a threat"),
    (43, "asia", "business", "Reliance seeks satellite capacity to rival Starlink"),
    (44, "asia", "climate", "Odisha opens 448 cyclone shelters; ₹20.5 crore released"),
]

STATS = [
    ("$81.3bn", "largest share sale ever — lists today"),
    ("589m", "children in conflict zones, a record"),
    ("47,000", "evacuated in Odisha ahead of Akvan"),
    ("299.25 GW", "India's renewable capacity, govt says"),
]


# ---------------------------------------------------------------------------
# Panel + page composition
# ---------------------------------------------------------------------------

def render_panel(cnv, box, spec, big):
    num, region, _field, kicker, source, tag, scene, head, deck = spec
    x0, y0, x1, y1 = box
    cnv.rectangle(box, fill=PANEL_BG, outline=RULE, width=1)
    art_h = 68 if big else 54
    scene(cnv, (x0 + 1, y0 + 1, x1 - 1, y0 + art_h))
    # certainty stamp on the art, top right
    tag_chip(cnv, x1 - 6, y0 + 11, tag)
    cnv.line([x0, y0 + art_h, x1, y0 + art_h], fill=RULE, width=1)
    inner_w = (x1 - x0) - 16
    tx = x0 + 8
    ty = y0 + art_h + 5
    chip = 20 if big else 17
    num_chip(cnv, tx + chip // 2, ty + chip // 2, num, chip, GOLD, NAVY)
    put(cnv, tx + chip + 6, ty + (3 if big else 2), kicker,
        F(SANS_B, 11 if big else 9), fill=REGION[region])
    put_r(cnv, x1 - 8, ty + (3 if big else 2), source,
          F(SANS_B, 8), fill=GREY)
    ty += chip + 4
    hfont = fit_font(cnv, head, SERIF_B, inner_w, 2, 18 if big else 15, 11)
    ty = paint_lines(cnv, tx, ty, wrap(cnv, head, hfont, inner_w), hfont,
                     int(hfont.size * 1.16))
    dfont = fit_font(cnv, deck, SANS, inner_w, 3, 10.5 if big else 10, 8.5)
    paint_lines(cnv, tx, ty + 2, wrap(cnv, deck, dfont, inner_w), dfont,
                int(dfont.size * 1.32), fill=_hex("33383e"))


def masthead(cnv):
    cnv.rectangle([0, 0, PAGE, 98], fill=NAVY)
    # red date chip
    cnv.rectangle([EDGE, 11, EDGE + 60, 87], fill=RED)
    put(cnv, EDGE + 30, 17, "NOV", F(SANS_B, 11), fill=_hex("ffffff"),
        anchor="ma")
    put(cnv, EDGE + 30, 28, "19", F(SERIF_BLK, 32), fill=_hex("ffffff"),
        anchor="ma")
    put(cnv, EDGE + 30, 68, "THU · 2026", F(SANS_B, 8), fill=_hex("ffffff"),
        anchor="ma")
    spaced(cnv, 88, 10, "THE WORLD IN A DAY", F(SANS_B, 13), GOLD_L,
           tracking=3)
    put(cnv, 88, 26, "Thursday 19 November 2026", F(SERIF_BLK, 36),
        fill=_hex("ffffff"))
    put(cnv, 88, 72,
        "Everything on this page happened, or was first reported, on "
        "Thursday 19 November 2026.", F(SERIF_I, 12), fill=CREAM)
    put_r(cnv, PAGE - EDGE, 12, "44 STORIES", F(SERIF_B, 17),
          fill=_hex("ffffff"))
    put_r(cnv, PAGE - EDGE, 36, "6 REGIONS · ONE PAGE", F(SANS_B, 10),
          fill=GOLD_L)
    put_r(cnv, PAGE - EDGE - 196, 66, "HOW SURE:", F(SANS_B, 8), fill=CREAM)
    x = PAGE - EDGE
    for tag in ("FORECAST", "CLAIM", "CONFIRMED"):
        w = tag_chip(cnv, x, 66, tag)
        x -= w + 6


def taxonomy(cnv):
    counts = {}
    for spec in TOP + MINI_A + MINI_B:
        counts[spec[2]] = counts.get(spec[2], 0) + 1
    for _n, _r, field, _t in ALSO:
        counts[field] = counts.get(field, 0) + 1
    short = {"diplomacy": "DIPLOMACY", "war": "WAR", "business": "BUSINESS",
             "climate": "CLIMATE", "politics": "POLITICS",
             "science": "SCIENCE", "culture": "CULTURE",
             "society": "SOCIETY"}
    total = sum(counts.values())
    x = EDGE
    y0, y1 = 102, 122
    for field, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        w = SPAN * count / total
        cnv.rectangle([x, y0, x + w - 2, y1], fill=FIELD_COLOR[field])
        label = f"{short[field]} {count}"
        font = fit_font(cnv, label, SANS_B, w - 8, 1, 9, 7)
        put(cnv, x + (w - 2) / 2, y0 + 10, label, font,
            fill=_hex("ffffff"), anchor="mm")
        x += w


def timeline(cnv):
    y = 130
    put(cnv, EDGE, y, "THE DAY IN UTC", F(SANS_B, 10), fill=NAVY)
    items = ["OVERNIGHT Kerch Bridge hit again",
             "04:45 Trump–Xi sit down",
             "06:30 first trilateral talks",
             "09:00 ICJ verdict read",
             "14:30 ANT opens on Nasdaq",
             "FRI 06:30 Akvan landfall due"]
    text = "   ·   ".join(items)
    font = fit_font(cnv, text, SANS, SPAN - 118, 1, 10.5, 8)
    put(cnv, EDGE + 118, y, text, font, fill=_hex("33383e"))
    cnv.line([EDGE, y + 17, PAGE - EDGE, y + 17], fill=RULE, width=1)


def bottom_left(cnv):
    spaced(cnv, EDGE, 678, "WHERE IT HAPPENED", F(SANS_B, 13), NAVY,
           tracking=1)
    cnv.line([EDGE, 696, EDGE + 342, 696], fill=INK, width=2)
    paint_map(cnv, (EDGE, 704, EDGE + 342, 856))
    legend = [("Europe", "europe"), ("Asia", "asia"),
              ("Americas", "americas"), ("Middle East", "mideast"),
              ("Oceania", "oceania"), ("Global", "global")]
    lx = EDGE
    for name, key in legend:
        cnv.ellipse([lx, 864, lx + 8, 872], fill=REGION[key])
        put(cnv, lx + 12, 862, name, F(SANS, 9.5))
        lx += 16 + tw(cnv, name, F(SANS, 9.5)) + 10
    put(cnv, EDGE, 878,
        "Pins 1–10. Panel 11 (India–Japan 2+2) is unpinned: venue "
        "unconfirmed.", F(SANS, 9), fill=GREY)
    # stats, 2 x 2
    sy = 896
    for i, (big, cap) in enumerate(STATS):
        cx = EDGE + (i % 2) * 174
        cy = sy + (i // 2) * 33
        put(cnv, cx, cy, big, F(SERIF_B, 16), fill=NAVY)
        capf = fit_font(cnv, cap, SANS, 168, 1, 8.5, 7)
        put(cnv, cx, cy + 20, cap, capf, fill=GREY)


def bottom_right(cnv):
    x0 = EDGE + 356
    spaced(cnv, x0, 678, "ALSO ON THURSDAY 19 NOVEMBER", F(SANS_B, 13),
           NAVY, tracking=1)
    put_r(cnv, PAGE - EDGE, 678, "33 MORE STORIES", F(SANS_B, 10), fill=GREY)
    cnv.line([x0, 696, PAGE - EDGE, 696], fill=INK, width=2)
    col_w = (PAGE - EDGE - x0 - 16) // 2
    halves = [ALSO[:17], ALSO[17:]]
    for ci, items in enumerate(halves):
        cx = x0 + ci * (col_w + 16)
        iy = 706
        for num, region, _field, text in items:
            disc(cnv, cx + 8, iy + 6, 7, num, REGION[region])
            font = fit_font(cnv, text, SANS, col_w - 22, 1, 11, 9)
            put(cnv, cx + 21, iy, text, font)
            iy += 14.8


def date_check(cnv):
    y0, y1 = 960, 992
    cnv.rectangle([EDGE, y0, PAGE - EDGE, y1], fill=_hex("f3e0da"),
                  outline=RED, width=1)
    title = "DATE CHECK — LEFT OUT ON PURPOSE, FIRST REPORTED BEFORE THURSDAY:  "
    body = ("the EU's €45bn Ukraine loan & Voyager 1's light-day moment "
            "(Wed) · Van Gogh's $190.4m record, sold Wed night in New "
            "York · Nvidia's results, the Board of Peace report, the "
            "Knesset vote & the Deutsche Bank files (Tue).")
    font = F(SANS, 9.5)
    lines = wrap(cnv, title + body, font, SPAN - 20)
    ty = y0 + 6
    for line in lines[:2]:
        put(cnv, EDGE + 10, ty, line, font, fill=_hex("33383e"))
        ty += 13


def footer(cnv):
    cnv.line([EDGE, 996, PAGE - EDGE, 996], fill=INK, width=1)
    put(cnv, EDGE, 1003,
        "Every story happened, or was first reported, on Thursday "
        "19 November 2026; contested claims are marked as claims. "
        "Original drawings.", F(SANS, 9.5), fill=GREY)
    put_r(cnv, PAGE - EDGE, 1003,
          "Sources: Reuters · AP · AFP · BBC · Al Jazeera · NASA · IMD · "
          "ReliefWeb · Xinhua", F(SANS, 9.5), fill=GREY)


def compose():
    img = Image.new("RGB", (PAGE, PAGE), PAPER)
    cnv = ImageDraw.Draw(img)
    masthead(cnv)
    taxonomy(cnv)
    timeline(cnv)
    # three large panels
    edges = [EDGE + round(i * SPAN / 3) for i in range(4)]
    for i, spec in enumerate(TOP):
        render_panel(cnv, (edges[i] + (5 if i else 0), 154,
                           edges[i + 1] - (5 if i < 2 else 0), 344),
                     spec, big=True)
    # two rows of four mini panels
    edges = [EDGE + round(i * SPAN / 4) for i in range(5)]
    for row, specs, (ry0, ry1) in ((0, MINI_A, (350, 508)),
                                   (1, MINI_B, (514, 672))):
        for c, spec in enumerate(specs):
            render_panel(cnv, (edges[c] + (5 if c else 0), ry0,
                               edges[c + 1] - (5 if c < 3 else 0), ry1),
                         spec, big=False)
    bottom_left(cnv)
    bottom_right(cnv)
    date_check(cnv)
    footer(cnv)
    return img


def main():
    import hashlib
    img = compose()
    img.save(OUT, format="PNG")
    data = open(OUT, "rb").read()
    print("wrote", OUT, len(data), "bytes, sha256",
          hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    main()
