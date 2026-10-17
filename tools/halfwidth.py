"""Proportional half-width (single-byte) glyphs, as in the PS3 patch.
The game draws a single-byte character from its own 40 px cell and moves the pen by size/2 (+ spacing/2).
We redraw 0x20-0x7D in 俊羽圓體 at each letter's natural width and patch the exe (exepatch.py) to move the pen by
size * ADV[byte] / 28 instead: ADV is the advance in atlas px at the engine's 28 px reference (a full-width
character advances 28). ü / ó live in the never-used "#" / "]" slots (build.py ALIAS)."""
import os, functools
import numpy as np
from PIL import Image, ImageDraw
import pcglyph
SLOT = {"#": "ü", "]": "ó"}                  # slot -> character drawn there
X0, BASE = 6, 30                             # pen x and baseline in the 40 px cell (the original Latin sits at x 5-18, y 6-29)

def latin_weight():
    """YuPearl-Regular.ttf (1.011) draws broken Latin letters and digits (its kanji are fine), so the Regular build
    takes its half-width glyphs from Medium, as the PS3 patch did"""
    w = os.environ.get("WEIGHT", "Medium")
    return "Medium" if w == "Regular" else w

def chars():
    return [chr(c) for c in range(0x20, 0x7E)]

@functools.lru_cache(None)
def adv_table():
    """byte -> advance (atlas px, 28 = one full-width cell); bytes we do not draw keep the original 14 (= size/2)"""
    size = pcglyph.calibrate("80", os.path.join(pcglyph.paths.WORK, "fnt_main"))[0]
    f = pcglyph.font(size, latin_weight())
    t = bytearray([14]) * 256
    for ch in chars():
        t[ord(ch)] = max(1, min(255, int(round(f.getlength(SLOT.get(ch, ch))))))
    return bytes(t)

def width(ch):
    """advance of a single-byte character in full-width units (for line breaking)"""
    return adv_table()[ord(ch)] / 28.0

def render(ch, kind, pal_body, pal_out):
    """half-width glyph for byte ch -> (body, outline) cells"""
    _, _, cell, _ = pcglyph.ATLAS[kind]
    s80 = pcglyph.calibrate("80", os.path.join(pcglyph.paths.WORK, "fnt_main"))[0]
    s = s80 if kind == "80" else pcglyph.calibrate("14", os.path.join(pcglyph.paths.WORK, "fnt_main"))[0]
    k = s / s80
    im = Image.new("L", (cell, cell), 0)
    ImageDraw.Draw(im).text((X0 * k, BASE * k * (40.0 / 40)), SLOT.get(ch, ch), fill=255, font=pcglyph.font(s, latin_weight()), anchor="ls")
    m = np.asarray(im, np.float32) / 255
    return pcglyph.compose(m, kind, pal_body, pal_out)
