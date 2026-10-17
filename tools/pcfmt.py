"""PC file formats: KCAP archives (.pak) and the 8-bit palette TGA font atlases.
KCAP: "KCAP", u32, u32, u32 count; entries of 0x2C bytes: u32 compressed, name[24] (cp932), u32 x2 (timestamp),
u32 offset, u32 size. Compressed data: u32 packed size, u32 unpacked size, LZSS (4 KiB window, start 0xFEE, flags LSB first).
We write LZSS streams as literals only (flag byte 0xFF + 8 literals): the game's own decoder reads them, and it is fast."""
import struct
import numpy as np
from pc_kcap import lzss

def kcap_read(path):
    """-> (header 16 bytes, [dict(name, comp, ts, data)]) ; data is decompressed"""
    d = open(path, "rb").read()
    assert d[:4] == b"KCAP", path
    n = struct.unpack("<I", d[12:16])[0]; out = []
    for k in range(n):
        e = d[16 + k * 0x2C:16 + (k + 1) * 0x2C]
        comp = struct.unpack("<I", e[:4])[0]; name = e[4:28]; ts = e[28:36]
        off, size = struct.unpack("<II", e[36:44])
        stored = d[off:off + size]; raw = stored
        if comp == 1:
            psize, usize = struct.unpack("<II", raw[:8]); raw = lzss(raw[8:8 + psize], usize)
        out.append(dict(name=name.split(b"\0")[0].decode("cp932"), rawname=name, comp=comp, ts=ts, data=raw,
                        stored=stored, orig=raw))
    return d[:16], out

def lzss_literal(b):
    out = bytearray()
    for i in range(0, len(b), 8):
        ch = b[i:i + 8]; out.append((1 << len(ch)) - 1); out += ch
    return bytes(out)

def kcap_write(path, header, ents):
    n = len(ents); off = 16 + 0x2C * n
    tab = bytearray(); blobs = []
    for e in ents:
        if "stored" in e and e["data"] == e["orig"]:
            blob = e["stored"]                       # unchanged: keep the original (compressed) bytes
        elif e["comp"] == 1:
            p = lzss_literal(e["data"]); blob = struct.pack("<II", len(p), len(e["data"])) + p
        else:
            blob = e["data"]                         # directory placeholders (comp 0xCCCCCCCC) and stored items
        tab += struct.pack("<I", e["comp"]) + e["rawname"] + e["ts"] + struct.pack("<II", off, len(blob))
        blobs.append(blob); off += len(blob)
    with open(path, "wb") as f:
        f.write(header[:12] + struct.pack("<I", n) + tab)
        for b in blobs: f.write(b)

def tga_read(b):
    """8-bit colour-mapped TGA -> (header bytes, palette (n,4) BGRA, pixels (h,w) top row first, bottom_up flag)"""
    idl, cmt, typ, cfirst, clen, cbits = struct.unpack("<BBBHHB", b[:8])
    x, y, w, h, bpp, desc = struct.unpack("<HHHHBB", b[8:18])
    assert typ == 1 and bpp == 8 and cbits == 32 and cfirst == 0, (typ, bpp, cbits, cfirst)
    po = 18 + idl; pal = np.frombuffer(b[po:po + 4 * clen], np.uint8).reshape(clen, 4).copy(); po += 4 * clen
    a = np.frombuffer(b[po:po + w * h], np.uint8).reshape(h, w)
    up = not desc & 0x20
    return b[:18 + idl], pal, (a[::-1] if up else a).copy(), up

def tga_write(head, pal, a, up):
    h, w = a.shape
    head = bytearray(head); struct.pack_into("<HH", head, 12, w, h)
    return bytes(head) + pal.tobytes() + (a[::-1] if up else a).tobytes()
