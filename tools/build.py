"""Build the PC patch: scripts, font atlases and exe for the main game and Special Contents.
   python tools/build.py [--weight Regular] [--install]
Reads work/pc_text.pkl (tools/pc_text.py) and the original files in backup_original/.
Writes output/<weight>/{main,special}/{WA2.exe|WA2_Special.exe, script.pak, fnt.pak}; --install copies them into the game.
Encoding: cp932 where the font has the character (NEC-selected IBM kanji 0xED/0xEE -> their IBM codes 0xFA-0xFC,
the only ones the font has); everything else gets a new code from 0xF040-0xF0FC, 0x8540-0x85FC, 0x8640-0x86FC.
Every ideograph in the atlases is redrawn in 俊羽圓體 (the subtitles are Traditional Chinese)."""
import os, sys, re, struct, pickle, shutil, argparse, unicodedata
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser(); ap.add_argument("--weight", default="Regular"); ap.add_argument("--install", action="store_true")
args = ap.parse_args()
os.environ["WEIGHT"] = args.weight
import paths, fonttable, pcglyph, exepatch, halfwidth
from pcfmt import kcap_read, kcap_write, tga_read, tga_write

PLANS = pickle.load(open(os.path.join(paths.WORK, "pc_text.pkl"), "rb"))
EXTRA = [(0xF0C1, 0xF0FC), (0x8540, 0x85FC), (0x8640, 0x86FC)]
ROWS = 102
# characters cp932 cannot encode, written with the identical-looking character the font has (as in the PS3 build)
NORM = {"〜": "～", "·": "・", "‧": "・", "—": "―", "︰": "：", "﹐": "，", ",": "，", "~": "～"}
# accented letters: drawn into half-width slots no script uses (halfwidth.SLOT)
ALIAS = {"ü": "#", "ó": "]"}
HALF = {chr(c) for c in range(0x20, 0x7E)} - set(",<>|\\")      # half-width glyphs the font has (0x20-0x7D)

T0 = fonttable.original(os.path.join(paths.BACKUP, "main", "WA2.exe"))
CELL_CHAR = T0.chars()
IBM = {}
for c in range(0xFA40, 0xFC4C):
    try: IBM.setdefault(struct.pack(">H", c).decode("cp932"), c)
    except UnicodeDecodeError: pass
def cp932_code(ch):
    try: b = ch.encode("cp932")
    except UnicodeEncodeError: return None
    if len(b) != 2: return None
    c = struct.unpack(">H", b)[0]
    if b[0] in (0xED, 0xEE): c = IBM.get(ch)
    return c if c is not None and T0.code_cell(c) is not None else None

# ---- tokens and the set of new glyphs ----
TOK = re.compile(r"\\[nk]|<R|<[WSF]\d*|[|>]")
def tokens(t):
    pos = 0
    for mm in TOK.finditer(t):
        for ch in t[pos:mm.start()]: yield "ch", ch
        yield "tok", mm.group(); pos = mm.end()
    for ch in t[pos:]: yield "ch", ch
need = set()
for m in PLANS.values():
    for t in m.values():
        for kind, v in tokens(t):
            if kind != "ch" or v in HALF or v in ALIAS: continue
            v = NORM.get(v, v)
            if cp932_code(v) is None: need.add(v)
need = sorted(need)
free = [c for lo, hi in [(0xF040, 0xF0FC), (0x8540, 0x85FC), (0x8640, 0x86FC)] for c in range(lo, hi + 1) if c & 0xFF != 0x7F]
assert len(need) <= len(free), (len(need), len(free))
NEW = dict(zip(need, free))
print("new glyphs:", len(NEW))
def enc(t):
    out = bytearray()
    for kind, v in tokens(t):
        if kind == "tok": out += v.encode(); continue
        if v in ALIAS: out += ALIAS[v].encode(); continue
        if v in HALF: out += v.encode(); continue
        v = NORM.get(v, v)
        c = NEW.get(v) or cp932_code(v)
        out += struct.pack(">H", c)
    return bytes(out)

# ---- exe ----
OUT = os.path.join(paths.OUTPUT, args.weight)
GAMES = {"main": (paths.GAME, "WA2.exe"), "special": (paths.SPECIAL, "WA2_Special.exe")}
TABLE = None
for which, (_, exe_name) in GAMES.items():
    exe = open(os.path.join(paths.BACKUP, which, exe_name), "rb").read()
    exe, T = exepatch.patch(exe, which, EXTRA, halfwidth.adv_table())
    assert T.total <= ROWS * fonttable.COLS
    assert all(T.cell[c] == T0.cell[c] for c in T0.cell)
    TABLE = T
    os.makedirs(os.path.join(OUT, which), exist_ok=True)
    open(os.path.join(OUT, which, exe_name), "wb").write(exe)
assert all(TABLE.code_cell(c) is not None for c in NEW.values())

# ---- scripts ----
# Special Contents pages the side story differently in 5002: it has its own page map (novel_map.py, WA2_JP=pc_jp_special)
NOVEL_SP = os.path.join(paths.WORK, "novel_map_special.pkl")
NOVEL_SP = pickle.load(open(NOVEL_SP, "rb")) if os.path.exists(NOVEL_SP) else {}
for which in GAMES:
    h, E = kcap_read(os.path.join(paths.BACKUP, which, "script.pak"))
    byname = {e["name"]: e for e in E}; n_ok = 0
    for name, m in PLANS.items():
        e = byname.get(name + ".txt")
        main = open(os.path.join(paths.JP_DIR, name + ".txt"), "rb").read()
        if e is not None and e["data"] != main and name in NOVEL_SP and which == "special":
            m = NOVEL_SP[name]; print("  special: %s.txt uses its own page map" % name)
        elif e is None or e["data"] != main:                    # only scripts identical to the ones we aligned
            print("  %s: %s.txt differs from the main game, left as is" % (which, name)); continue
        f = e["data"].split(b",")
        for i, t in m.items(): f[i] = enc(t)
        e["data"] = b",".join(f); n_ok += 1
    kcap_write(os.path.join(OUT, which, "script.pak"), h, E)
    print(which, "scripts patched:", n_ok)

# ---- font atlases ----
def is_ideo(ch):
    try: return unicodedata.name(ch).startswith(("CJK UNIFIED IDEOGRAPH", "CJK COMPATIBILITY IDEOGRAPH"))
    except ValueError: return False
REDRAW = {i: ch for i, ch in CELL_CHAR.items() if is_ideo(ch)}
print("redraw %d ideographs (%s)" % (len(REDRAW), args.weight))
CACHE = {}
def cells_for(kind, pb, po, A, cell):
    def put(i, b, o):
        r, c = divmod(i, fonttable.COLS)
        A[0][r*cell:(r+1)*cell, c*cell:(c+1)*cell] = b; A[1][r*cell:(r+1)*cell, c*cell:(c+1)*cell] = o
    D = os.path.join(paths.WORK, "fnt_main")
    pal = (pb.tobytes(), po.tobytes())             # cells are palette indices: the main game and Special have different palettes
    for i, ch in list(REDRAW.items()) + [(TABLE.code_cell(c), ch) for ch, c in NEW.items()]:
        key = (kind, pal, ch)
        if key not in CACHE: CACHE[key] = pcglyph.render(ch, kind, pb, po, D)
        put(i, *CACHE[key])
    # half-width 0x20-0x7D: proportional 俊羽圓體 (ü / ó in the "#" / "]" slots), see halfwidth.py
    for ch in halfwidth.chars():
        key = (kind, pal, "half", ch)
        if key not in CACHE: CACHE[key] = halfwidth.render(ch, kind, pb, po)
        put(ord(ch) - 0x20, *CACHE[key])

for which in GAMES:
    h, E = kcap_read(os.path.join(paths.BACKUP, which, "fnt.pak"))
    byname = {e["name"]: e for e in E}
    for kind, (bf, of, cell, _) in pcglyph.ATLAS.items():
        hb, pb, Ab, ub = tga_read(byname[bf]["data"]); ho, po, Ao, uo = tga_read(byname[of]["data"])
        pad = lambda a: np.vstack([a, np.zeros((ROWS * cell - a.shape[0], a.shape[1]), np.uint8)])
        A = [pad(Ab), pad(Ao)]
        cells_for(kind, pb, po, A, cell)
        byname[bf]["data"] = tga_write(hb, pb, A[0], ub); byname[of]["data"] = tga_write(ho, po, A[1], uo)
    kcap_write(os.path.join(OUT, which, "fnt.pak"), h, E)
    print(which, "fnt.pak written")
open(os.path.join(OUT, "new_glyphs.txt"), "w", encoding="utf-8").write("".join(NEW))

if args.install:
    for which, (dst, exe_name) in GAMES.items():
        for n in (exe_name, "script.pak", "fnt.pak"):
            shutil.copyfile(os.path.join(OUT, which, n), os.path.join(dst, n))
    print("installed", args.weight)
