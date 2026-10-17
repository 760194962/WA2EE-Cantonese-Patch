"""Render lines with a built fnt.pak the way the game composes them (outline layer dark, body layer white).
   python tools/preview_line.py output/Regular/main out.png "text" ["text" ...]
Full-width characters advance 28 px, single bytes by the exe's advance table (.yue section)."""
import os, sys, struct
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths, fonttable
from pcfmt import kcap_read, tga_read
from pe import PE
d, out, texts = sys.argv[1], sys.argv[2], sys.argv[3:]
exe = [n for n in os.listdir(d) if n.endswith(".exe")][0]
which = "main" if exe == "WA2.exe" else "special"
p = PE(os.path.join(d, exe))
import re
tva = struct.unpack("<I", p.b[p.off(fonttable.EXES[which][1][1]):p.off(fonttable.EXES[which][1][1]) + 4])[0]
T = fonttable.Table(fonttable.read_ranges(p, tva))
new = open(os.path.join(os.path.dirname(d), "new_glyphs.txt"), encoding="utf-8").read()
free = [c for lo, hi in [(0xF040, 0xF0FC), (0x8540, 0x85FC), (0x8640, 0x86FC)] for c in range(lo, hi + 1) if c & 0xFF != 0x7F]
NEW = dict(zip(new, free))
_, E = kcap_read(os.path.join(d, "fnt.pak")); by = {e["name"]: e for e in E}
_, pb, A, _ = tga_read(by["本体80.tga"]["data"]); _, po, O, _ = tga_read(by["袋影80.tga"]["data"])
IBM = {}
for c in range(0xFA40, 0xFC4C):
    try: IBM.setdefault(struct.pack(">H", c).decode("cp932"), c)
    except UnicodeDecodeError: pass
def code(ch):
    if ch in NEW: return NEW[ch]
    b = ch.encode("cp932")
    if len(b) == 1: return b[0]
    return IBM.get(ch) if b[0] in (0xED, 0xEE) else struct.unpack(">H", b)[0]

sec = [x for x in p.sec if x[0] == ".yue"][0]; ADV = p.b[sec[3] + 0x200:sec[3] + 0x300]
rows = []
for t in texts:
    for ln in t.split("\\n"):
        W = 40 * len(ln) + 40; img = np.full((44, W), 70.0); x = 0
        for ch in ln:
            c = code({"ü": "#", "ó": "]"}.get(ch, ch)); i = T.code_cell(c); r, cc = divmod(i, 80)
            b = A[r*40:(r+1)*40, cc*40:(cc+1)*40]; o = O[r*40:(r+1)*40, cc*40:(cc+1)*40]
            ab = pb[b, 3] / 255.0; ao = po[o, 3] / 255.0
            reg = img[2:42, x:x + 40]; reg[:] = reg * (1 - ao) + 15 * ao; reg[:] = reg * (1 - ab) + 255 * ab
            x += ADV[c] if c < 0x100 else 28
        rows.append(img[:, :max(x, 40)])
w = max(r.shape[1] for r in rows)
Image.fromarray(np.vstack([np.pad(r, ((0, 0), (0, w - r.shape[1])), constant_values=70) for r in rows]).astype(np.uint8)).save(out)
