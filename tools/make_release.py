"""Build the distributable patch kit (no game files: only what turns the user's own files into the patched ones).
   python tools/make_release.py v0.1-beta [--weight Regular]   -> output/release/WA2EE_Cantonese_<ver>/ and .zip
Compares output/<weight>/ (tools/build.py) with backup_original/ and stores
  exe        WA2D difference (COPY/INSERT/ZERO ops, as in the PS3 kit)
  script.pak the changed fields of the changed .txt entries (the Cantonese text only)
  fnt.pak    the changed 40/24 px cells of each atlas and the new atlas height
in patch/patch.dat; tools/release/apply.py (copied into the kit, standard library only) applies it."""
import os, sys, struct, hashlib, lzma, shutil, zipfile, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
from pcfmt import kcap_read, tga_read
import numpy as np

def wa2d_encode(src, dst, block=16):
    """COPY/INSERT/ZERO ops turning src into dst (see apply.wa2d_apply)."""
    idx = {}
    for o in range(0, len(src) - block + 1, block):
        k = src[o:o + block]
        if k != bytes(block): idx.setdefault(k, o)
    ops = bytearray(); lit = bytearray(); p = 0; n = len(dst)
    def flush():
        if lit: ops.extend(b"\x02" + struct.pack(">I", len(lit)) + lit); lit.clear()
    while p < n:
        if dst[p] == 0:
            q = p
            while q < n and dst[q] == 0: q += 1
            if q - p >= 32: flush(); ops.extend(b"\x03" + struct.pack(">I", q - p)); p = q; continue
        so = idx.get(dst[p:p + block])
        if so is None:
            for d in range(1, block):
                s2 = idx.get(dst[p - d:p - d + block]) if p >= d else None
                if s2 is not None and src[s2 + d:s2 + d + 1] == dst[p:p + 1]: so = s2 + d; break
        if so is None or src[so:so + 8] != dst[p:p + 8]:
            lit.append(dst[p]); p += 1; continue
        ln = 0
        while p + ln < n and so + ln < len(src) and src[so + ln] == dst[p + ln]: ln += 1
        if ln < 24: lit.extend(dst[p:p + ln]); p += ln; continue
        flush(); ops.extend(b"\x01" + struct.pack(">II", so, ln)); p += ln
    flush()
    return (b"WA2D1" + hashlib.sha1(src).digest() + hashlib.sha1(dst).digest() + struct.pack(">I", len(dst))
            + lzma.compress(bytes(ops), preset=9))

GAMES = {"main": ("WHITE ALBUM2", "WA2.exe"), "special": ("WHITE ALBUM2 Special Contents", "WA2_Special.exe")}
CELL = {"本体80.tga": 40, "袋影80.tga": 40, "14pt本体.tga": 24, "14pt袋.tga": 24}

def build_patch(weight):
    meta = {"games": {}}; blobs = bytearray()
    def put(b):
        o = len(blobs); blobs.extend(b); return [o, len(b)]
    for which, (folder, exe_name) in GAMES.items():
        src_dir = os.path.join(paths.BACKUP, which); dst_dir = os.path.join(paths.OUTPUT, weight, which)
        g = meta["games"][which] = {"folder": folder, "exe": exe_name, "sha1": {}, "files": {}}
        for n in (exe_name, "script.pak", "fnt.pak"):
            g["sha1"][n] = hashlib.sha1(open(os.path.join(src_dir, n), "rb").read()).hexdigest()
        # exe
        a = open(os.path.join(src_dir, exe_name), "rb").read(); b = open(os.path.join(dst_dir, exe_name), "rb").read()
        g["files"][exe_name] = {"wa2d": put(wa2d_encode(a, b))}
        # script.pak: changed fields only
        _, A = kcap_read(os.path.join(src_dir, "script.pak")); _, B = kcap_read(os.path.join(dst_dir, "script.pak"))
        sc = {}
        for ea, eb in zip(A, B):
            assert ea["name"] == eb["name"]
            if ea["data"] == eb["data"]: continue
            assert ea["name"].endswith(".txt"), ea["name"]
            fa, fb = ea["data"].split(b","), eb["data"].split(b",")
            assert len(fa) == len(fb)
            sc[ea["name"]] = {str(i): put(y) for i, (x, y) in enumerate(zip(fa, fb)) if x != y}
        g["files"]["script.pak"] = {"fields": sc}
        # fnt.pak: changed cells
        _, A = kcap_read(os.path.join(src_dir, "fnt.pak")); _, B = kcap_read(os.path.join(dst_dir, "fnt.pak"))
        ft = {}
        for ea, eb in zip(A, B):
            if ea["data"] == eb["data"]: continue
            cs = CELL[ea["name"]]
            _, pa, xa, _ = tga_read(ea["data"]); _, pb_, xb, _ = tga_read(eb["data"])
            assert (pa == pb_).all() and xa.shape[1] == xb.shape[1]
            xa2 = np.zeros_like(xb); xa2[:xa.shape[0]] = xa
            cols = xb.shape[1] // cs; rows = xb.shape[0] // cs
            idx = []; pix = bytearray()
            for r in range(rows):
                for c in range(cols):
                    cb = xb[r*cs:(r+1)*cs, c*cs:(c+1)*cs]
                    if not np.array_equal(cb, xa2[r*cs:(r+1)*cs, c*cs:(c+1)*cs]):
                        idx.append(r * cols + c); pix += cb.tobytes()
            ft[ea["name"]] = {"height": int(xb.shape[0]), "cell": cs, "cells": put(struct.pack("<%dH" % len(idx), *idx)), "pixels": put(bytes(pix))}
            print("  %s %s: %d cells" % (which, ea["name"], len(idx)))
        g["files"]["fnt.pak"] = {"atlases": ft}
        # the result, so apply.py can verify what it wrote
        g["result_sha1"] = {n: hashlib.sha1(open(os.path.join(dst_dir, n), "rb").read()).hexdigest()
                            for n in (exe_name, "script.pak", "fnt.pak")}
    head = json.dumps(meta, ensure_ascii=False).encode("utf-8")
    return b"WA2EEP1" + struct.pack("<I", len(head)) + head + lzma.compress(bytes(blobs), preset=9)

README = """WHITE ALBUM2 EXTENDED EDITION（PC）粵語化補丁 {ver}（測試版）

內容：IC 全篇（二周目分支在內）同外傳「雪が解け、そして雪が降るまで」，
      主程式（WHITE ALBUM2）同 Special Contents 兩邊都會打補丁。
譯文：採集自raymondsakura YouTube頻道公開影片
      字幕冇嘅台詞仲係日文（千晶嘅兩場，約 80 句）。CC 同 coda 未有中文。
字體：俊羽圓體（YuPearl），粵字缺字用源泉圓體（GenSen Rounded）補，兩款都係 SIL OFL 字體。

需要：
  - WHITE ALBUM2 EXTENDED EDITION（PC 版，未改過嘅原版檔案）
  - 電腦上有 Python 3（python.org，裝嗰陣勾選 Add to PATH）

安裝：
  1. 雙擊「安裝補丁.bat」
  2. 將遊戲安裝文件夾拖入個黑色視窗，再按 Enter
     （即係入面有「WHITE ALBUM2」同「WHITE ALBUM2 Special Contents」嘅文件夾；
       直接拖「WHITE ALBUM2」文件夾都得）
  3. 見到「完成」就可以開遊戲

還原：雙擊「還原原版.bat」，一樣拖入遊戲文件夾。原版檔案備份喺遊戲文件夾入面嘅「粵語補丁備份」。

注意：
  - 遊戲裝喺 Program Files 嘅話，可能要用右鍵「以系統管理員身分執行」。
  - 補丁會換 WA2.exe / WA2_Special.exe、script.pak、fnt.pak。打完補丁之後 fnt.pak 會大（約 40MB），屬正常。
  - 舊存檔入面嘅回放記錄可能會顯示怪字，屬正常；新顯示嘅句子唔受影響。
  - 測試版：如果見到錯字、亂碼、字出界，請截圖連同大概位置回報。
"""
BAT = r"""@echo off
chcp 65001 >nul
setlocal
set "BASE=%~dp0"
set "PY="
for %%C in ("py -3" "python" "python3") do (
  if not defined PY ( %%~C -c "import lzma" >nul 2>nul && set "PY=%%~C" )
)
if not defined PY (
  for /d %%P in ("%LOCALAPPDATA%\Programs\Python\Python3*" "%LOCALAPPDATA%\Python\pythoncore-*") do (
    if not defined PY ( if exist "%%P\python.exe" ( "%%P\python.exe" -c "import lzma" >nul 2>nul && set PY="%%P\python.exe" ) )
  )
)
if not defined PY ( echo [錯誤] 搵唔到 Python 3，請先安裝 python.org 嘅 Python 3。 & goto :end )
set "GAME=%~1"
if not defined GAME set /p "GAME=請將遊戲文件夾拖入呢個視窗，然後按 Enter: "
set "GAME=%GAME:"=%"
%PY% "%BASE%patch\apply.py" {args} "%GAME%"
:end
echo.
pause
"""

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("version"); ap.add_argument("--weight", default="Regular")
    a = ap.parse_args()
    name = "WA2EE_Cantonese_" + a.version
    kit = os.path.join(paths.OUTPUT, "release", name)
    if os.path.exists(kit): shutil.rmtree(kit)
    os.makedirs(os.path.join(kit, "patch"))
    data = build_patch(a.weight)
    open(os.path.join(kit, "patch", "patch.dat"), "wb").write(data)
    shutil.copyfile(os.path.join(paths.TOOLS, "release", "apply.py"), os.path.join(kit, "patch", "apply.py"))
    open(os.path.join(kit, "說明.txt"), "w", encoding="utf-8-sig", newline="\r\n").write(README.format(ver=a.version))
    open(os.path.join(kit, "安裝補丁.bat"), "w", encoding="utf-8", newline="\r\n").write(BAT.replace("{args}", ""))
    open(os.path.join(kit, "還原原版.bat"), "w", encoding="utf-8", newline="\r\n").write(BAT.replace("{args}", "--undo"))
    for lic in ("SIL_Open_Font_License_1.1.txt",):
        src = os.path.join(paths.FONT_DIR, "YuPearl-1.011", lic)
        if os.path.exists(src): shutil.copyfile(src, os.path.join(kit, "patch", "OFL.txt"))
    z = kit + ".zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(kit):
            for f in files:
                p = os.path.join(root, f); zf.write(p, os.path.join(name, os.path.relpath(p, kit)))
    print("kit:", kit, "\nzip:", z, os.path.getsize(z), "bytes")
