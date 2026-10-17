"""Draw glyphs for the PC font atlases (fnt.pak).
Each size has two 8-bit palette atlases: 本体 (body) and 袋影/袋 (outline). Index meaning (from the palettes):
  本体80   0-31 = outline coverage (alpha 0, grey ramp), 32-63 = letter alpha (white)
  袋影80   0-63 = outline alpha
  14pt本体 0-31 = letter alpha
  14pt袋   0-42 = outline alpha
Size and position are calibrated against kanji that are already in the atlas, so new glyphs line up with the old ones."""
import functools, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import paths
from pcfmt import tga_read

ATLAS = {   # name: (body file, outline file, cell px, outline radius px)
    "80": ("本体80.tga", "袋影80.tga", 40, 2),
    "14": ("14pt本体.tga", "14pt袋.tga", 24, 1),
}
CALIB = "亜唖娃阿哀愛挨姶逢葵茜穐悪握渥旭葦芦鯵梓圧斡扱宛姐虻飴絢綾鮎或粟袷安庵按暗案闇鞍杏"

@functools.lru_cache(None)
def font(size, weight=None):
    weight = weight or os.environ.get("WEIGHT", "Medium")
    return ImageFont.truetype(paths.YUPEARL % weight, size)

@functools.lru_cache(None)
def fallback(size):
    """源泉圓體 in the weight matching 俊羽圓體 (for the Cantonese characters 俊羽圓體 lacks)"""
    w = {"Light": "L", "Regular": "R", "Medium": "M"}[os.environ.get("WEIGHT", "Medium")]
    return ImageFont.truetype(paths.GENSEN.replace("-M.otf", "-%s.otf" % w), size)

@functools.lru_cache(None)
def _cmap(weight=None):
    weight = weight or os.environ.get("WEIGHT", "Medium")
    from fontTools.ttLib import TTFont
    return set(TTFont(paths.YUPEARL % weight).getBestCmap())

def _ink(ch, size, cell):
    f = font(size) if ord(ch) in _cmap() else fallback(size)
    im = Image.new("L", (cell * 2, cell * 2), 0)
    ImageDraw.Draw(im).text((cell, cell), ch, fill=255, font=f, anchor="mm")
    return im

def _bbox_stats(boxes):
    b = np.array(boxes, float)
    return np.median(b[:, 2] - b[:, 0]), np.median(b[:, 3] - b[:, 1]), np.median((b[:, 0] + b[:, 2]) / 2), np.median((b[:, 1] + b[:, 3]) / 2)

@functools.lru_cache(None)
def calibrate(kind, atlas_dir):
    """-> (font size, ink centre x, y in the cell) matching the original kanji"""
    import fonttable
    body, _, cell, _ = ATLAS[kind]
    _, pal, a, _ = tga_read(open(atlas_dir + "/" + body, "rb").read())
    lo = 32 if kind == "80" else 1
    T = fonttable.original(paths.BACKUP + "/main/WA2.exe"); inv = {v: k for k, v in T.chars().items()}
    ob = []
    for ch in CALIB:
        r, c = divmod(inv[ch], 80); g = a[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell]
        ys, xs = np.where(g >= lo)
        if len(xs): ob.append((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    W, H, cx, cy = _bbox_stats(ob)
    best = None
    for s in range(cell // 3, cell + 4):
        nb = [_ink(ch, s, cell).getbbox() for ch in CALIB]
        w, h, _, _ = _bbox_stats([b for b in nb if b])
        err = abs(w - W) + abs(h - H)
        if best is None or err < best[0]: best = (err, s)
    return best[1], cx, cy

def _nearest(levels, idx, v):
    """map coverage v (0..1 array) to the palette index whose level is closest"""
    levels = np.asarray(levels, float); idx = np.asarray(idx)
    k = np.abs(v[..., None] * 255 - levels[None, None, :]).argmin(-1)
    return idx[k].astype(np.uint8)

def render(ch, kind, pal_body, pal_out, atlas_dir):
    """-> (body cell, outline cell) as palette indices"""
    _, _, cell, rad = ATLAS[kind]
    size, cx, cy = calibrate(kind, atlas_dir)
    im = _ink(ch, size, cell)
    b = im.getbbox()
    big = np.zeros((cell, cell), np.float32)
    if b:
        # place the ink box centre where the original kanji centres sit
        ox = int(round(cx - (b[0] + b[2]) / 2)); oy = int(round(cy - (b[1] + b[3]) / 2))
        canvas = Image.new("L", (cell, cell), 0); canvas.paste(im, (ox, oy)); big = np.asarray(canvas, np.float32) / 255
    return compose(big, kind, pal_body, pal_out)

def _scheme(kind, pal_body, pal_out):
    """(letter indices, rim indices or None, outline indices) for this pair of palettes"""
    if kind == "80" and len(pal_body) == 256:          # main game: 0-31 rim (alpha 0), 32-63 letter
        return np.arange(32, 64), np.arange(32), np.arange(64)
    if kind == "80":                                   # Special Contents: 16-entry alpha ramps
        return np.arange(len(pal_body)), None, np.arange(len(pal_out))
    return np.arange(32), None, np.arange(43)

def coverage(body, kind, pal_body):
    """palette indices of a 本体 cell -> letter coverage 0..1"""
    lv = pal_body[:, 3].astype(np.float32) / 255
    if kind == "80" and len(pal_body) == 256: return np.where(body >= 32, lv[body], 0)
    return lv[body]

def compose(m, kind, pal_body, pal_out):
    """letter coverage (cell x cell, 0..1) -> (body cell, outline cell) as palette indices"""
    rad = ATLAS[kind][3]
    o = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(2 * rad + 1)), np.float32) / 255
    o = np.asarray(Image.fromarray((o * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255
    o = np.maximum(o, m)
    li, ri, oi = _scheme(kind, pal_body, pal_out)
    body = _nearest(pal_body[li, 3], li, m)
    if ri is not None: body = np.where(m > 1 / 64, body, np.round(o * ri[-1]).astype(np.uint8))
    out = _nearest(pal_out[oi, 3], oi, o)
    return body.astype(np.uint8), out.astype(np.uint8)
