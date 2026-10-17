#!/usr/bin/env python3
"""WHITE ALBUM2 EXTENDED EDITION (PC) Cantonese patch - user-side patcher. Only the Python standard library is used.
    python patch/apply.py  <game folder>           install
    python patch/apply.py --undo <game folder>     put the original files back
<game folder>: the install folder, or "WHITE ALBUM2" and/or "WHITE ALBUM2 Special Contents" (one or both, any order).
Originals are copied to <each game folder>/粵語補丁備份/ before anything is written."""
import os, sys, re, struct, json, hashlib, lzma, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
BACKUP = "粵語補丁備份"

try: sys.stdout.reconfigure(errors="replace")
except Exception: pass

def die(msg): print("\n[錯誤] " + msg); sys.exit(1)
def sha1(b): return hashlib.sha1(b).hexdigest()

# ---------------- WA2D difference (exe) ----------------
def wa2d_apply(src, diff):
    if diff[:5] != b"WA2D1": die("差異文件格式唔啱")
    ssha, dsha, dlen = diff[5:25], diff[25:45], struct.unpack(">I", diff[45:49])[0]
    if hashlib.sha1(src).digest() != ssha: return None
    ops = lzma.decompress(diff[49:]); out = bytearray(); i = 0
    while i < len(ops):
        op = ops[i]; i += 1
        if op == 1: so, n = struct.unpack(">II", ops[i:i + 8]); i += 8; out += src[so:so + n]
        elif op == 2: n = struct.unpack(">I", ops[i:i + 4])[0]; i += 4; out += ops[i:i + n]; i += n
        elif op == 3: n = struct.unpack(">I", ops[i:i + 4])[0]; i += 4; out += bytes(n)
        else: die("差異文件損壞")
    if len(out) != dlen or hashlib.sha1(out).digest() != dsha: die("套用差異之後校驗失敗")
    return bytes(out)

# ---------------- KCAP (.pak) ----------------
def lzss(src, usize):
    win = bytearray(4096); wp = 0xFEE; out = bytearray(); i = 0; n = len(src)
    while len(out) < usize and i < n:
        flags = src[i]; i += 1
        for b in range(8):
            if len(out) >= usize or i >= n: break
            if flags >> b & 1:
                c = src[i]; i += 1; out.append(c); win[wp] = c; wp = (wp + 1) & 0xFFF
            else:
                lo, hi = src[i], src[i + 1]; i += 2
                off = lo | (hi & 0xF0) << 4
                for k in range((hi & 0x0F) + 3):
                    c = win[(off + k) & 0xFFF]; out.append(c); win[wp] = c; wp = (wp + 1) & 0xFFF
    return bytes(out)

def kcap_read(d):
    if d[:4] != b"KCAP": die("唔係 KCAP 封包")
    n = struct.unpack("<I", d[12:16])[0]; out = []
    for k in range(n):
        e = d[16 + k * 0x2C:16 + (k + 1) * 0x2C]
        comp = struct.unpack("<I", e[:4])[0]; off, size = struct.unpack("<II", e[36:44])
        raw = d[off:off + size]
        out.append(dict(name=e[4:28].split(b"\0")[0].decode("cp932"), comp=comp, head=e[:36], raw=raw))
    return d[:16], out

def data_of(e):
    if e["comp"] != 1: return e["raw"]
    psize, usize = struct.unpack("<II", e["raw"][:8])
    return lzss(e["raw"][8:8 + psize], usize)

def lzss_literal(b):
    out = bytearray()
    for i in range(0, len(b), 8):
        ch = b[i:i + 8]; out.append((1 << len(ch)) - 1); out += ch
    return bytes(out)

def kcap_write(path, header, ents):
    n = len(ents); off = 16 + 0x2C * n; tab = bytearray(); blobs = []
    for e in ents:
        if "new" in e and e["comp"] == 1:
            p = lzss_literal(e["new"]); blob = struct.pack("<II", len(p), len(e["new"])) + p
        elif "new" in e:
            blob = e["new"]                                  # stored uncompressed in the original too (e.g. 1010_070.txt)
        else:
            blob = e["raw"]
        tab += e["head"] + struct.pack("<II", off, len(blob)); blobs.append(blob); off += len(blob)
    with open(path, "wb") as f:
        f.write(header[:12] + struct.pack("<I", n) + tab)
        for b in blobs: f.write(b)

# ---------------- 8-bit palette TGA ----------------
def tga_patch(t, height, cell, idx, pix):
    idl, _, typ, cfirst, clen, cbits = struct.unpack("<BBBHHB", t[:8])
    w, h, bpp, desc = struct.unpack("<HHBB", t[12:18])
    if typ != 1 or bpp != 8: die("字庫格式唔啱")
    po = 18 + idl + clen * cbits // 8
    rows = [t[po + r * w:po + (r + 1) * w] for r in range(h)]
    up = not desc & 0x20
    if up: rows.reverse()                                    # top row first
    img = bytearray(b"".join(rows)) + bytes(w * (height - h))
    cols = w // cell; cs = cell * cell
    for k, ci in enumerate(idx):
        r, c = divmod(ci, cols); src = pix[k * cs:(k + 1) * cs]
        for y in range(cell):
            o = (r * cell + y) * w + c * cell
            img[o:o + cell] = src[y * cell:(y + 1) * cell]
    out_rows = [img[r * w:(r + 1) * w] for r in range(height)]
    if up: out_rows.reverse()
    head = bytearray(t[:po]); struct.pack_into("<H", head, 14, height)
    return bytes(head) + b"".join(out_rows)

# ---------------- main ----------------
def find_games(roots, meta):
    """each dragged path may be the install folder or either game folder: look in it, below it and beside it"""
    found = {}
    for root in roots:
        root = os.path.abspath(root)
        for which, g in meta["games"].items():
            for cand in (root, os.path.join(root, g["folder"]), os.path.join(os.path.dirname(root), g["folder"])):
                if which not in found and os.path.isfile(os.path.join(cand, g["exe"])): found[which] = cand
    return found

def dragged_paths(args):
    """paths from the command line and from WA2EE_GAME (what was dragged into the window: one or more paths,
    quoted when they contain spaces); an unquoted path with spaces is also tried whole"""
    raw = " ".join(args + [os.environ.get("WA2EE_GAME", "")]).strip()
    out = [a or b for a, b in re.findall(r'"([^"]+)"|(\S+)', raw)]
    whole = raw.replace('"', "").strip()
    if whole and whole not in out: out.append(whole)
    return [p for p in out if os.path.isdir(p)]

def main():
    args = [a for a in sys.argv[1:] if a]
    undo = "--undo" in args; args = [a for a in args if a != "--undo"]
    roots = dragged_paths(args)
    if not roots: die("搵唔到你拖入嘅文件夾，請再試一次")
    root = "、".join(roots)
    d = open(os.path.join(HERE, "patch.dat"), "rb").read()
    if d[:7] != b"WA2EEP1": die("patch.dat 格式唔啱")
    hl = struct.unpack("<I", d[7:11])[0]; meta = json.loads(d[11:11 + hl].decode("utf-8"))
    games = find_games(roots, meta)
    if not games: die("喺「%s」搵唔到 WA2.exe 或者 WA2_Special.exe" % root)
    def state(gdir, g):
        """'orig' / 'patched' / None per file"""
        st = {}
        for n in g["sha1"]:
            h = sha1(open(os.path.join(gdir, n), "rb").read())
            st[n] = "orig" if h == g["sha1"][n] else ("patched" if h == g["result_sha1"].get(n) else None)
        return st
    if undo:
        for which, gdir in games.items():
            g = meta["games"][which]; bk = os.path.join(gdir, BACKUP)
            have = [n for n in g["sha1"] if os.path.isfile(os.path.join(bk, n)) and sha1(open(os.path.join(bk, n), "rb").read()) == g["sha1"][n]]
            for n in have: shutil.copyfile(os.path.join(bk, n), os.path.join(gdir, n))
            st = state(gdir, g)
            if all(v == "orig" for v in st.values()):
                print("已還原：%s" % gdir)
            else:
                die("%s 入面以下檔案冇原版備份，還原唔到：%s\n請用遊戲原本嘅安裝程式重新安裝呢啲檔案。"
                    % (gdir, "、".join(n for n, v in st.items() if v != "orig")))
        print("\n完成"); return
    blobs = lzma.decompress(d[11 + hl:])
    blob = lambda r: blobs[r[0]:r[0] + r[1]]
    for which, gdir in games.items():
        g = meta["games"][which]; print("\n== %s ==" % gdir)
        bk = os.path.join(gdir, BACKUP)
        orig = {}; need_backup = []
        for n, want in g["sha1"].items():
            p_b, p_g = os.path.join(bk, n), os.path.join(gdir, n)
            if os.path.isfile(p_b) and sha1(open(p_b, "rb").read()) == want:
                orig[n] = open(p_b, "rb").read(); continue     # re-running starts from the backup
            b = open(p_g, "rb").read(); h = sha1(b)
            if h == want: orig[n] = b; need_backup.append(n); continue
            if h == g["result_sha1"].get(n):
                die("%s 已經係補丁版本，但係搵唔到原版備份。\n如果想重新打補丁，請先用遊戲原本嘅安裝程式還原呢個檔案。" % p_g)
            die("%s 唔係補丁對應嘅原版檔案（可能已經改過或者版本唔同）。\n如果之前打過其他補丁，請先還原原版。" % p_g)
        os.makedirs(bk, exist_ok=True)                          # only once every file checked out
        for n in need_backup: shutil.copyfile(os.path.join(gdir, n), os.path.join(bk, n))
        # exe
        exe = g["exe"]; new = wa2d_apply(orig[exe], blob(g["files"][exe]["wa2d"]))
        if new is None or sha1(new) != g["result_sha1"][exe]: die("%s 套用失敗" % exe)
        open(os.path.join(gdir, exe), "wb").write(new); print("  %s 完成" % exe)
        # script.pak
        h, E = kcap_read(orig["script.pak"]); sc = g["files"]["script.pak"]["fields"]
        for e in E:
            if e["name"] not in sc: continue
            f = data_of(e).split(b",")
            for i, r in sc[e["name"]].items(): f[int(i)] = blob(r)
            e["new"] = b",".join(f)
        kcap_write(os.path.join(gdir, "script.pak"), h, E); print("  script.pak 完成（%d 個劇本）" % len(sc))
        # fnt.pak
        h, E = kcap_read(orig["fnt.pak"]); ft = g["files"]["fnt.pak"]["atlases"]
        for e in E:
            if e["name"] not in ft: continue
            a = ft[e["name"]]; ib = blob(a["cells"])
            idx = struct.unpack("<%dH" % (len(ib) // 2), ib)
            e["new"] = tga_patch(data_of(e), a["height"], a["cell"], idx, blob(a["pixels"]))
            print("  %s：%d 格" % (e["name"], len(idx)))
        kcap_write(os.path.join(gdir, "fnt.pak"), h, E); print("  fnt.pak 完成")
    print("\n完成。原版檔案備份喺各遊戲文件夾入面嘅「%s」。" % BACKUP)

if __name__ == "__main__":
    main()
