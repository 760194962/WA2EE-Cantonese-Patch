"""Patch WA2.exe / WA2_Special.exe. Everything new goes into an added section ".yue" at the end of the file
(the exes have no relocations, no signature and no overlay):
  +0x000  font range list (the original 59 ranges + the new ones), see fonttable.py
  +0x200  advance table: 256 bytes, advance of a single-byte character in atlas px at the 28 px reference
  +0x300  code: replaces the half-width pen step "pen += size/2 + spacing/2" with
          "pen += (size * ADV[byte] + 14) / 28 + spacing/2" (proportional Latin, as in the PS3 patch)
The two `mov reg, imm32` that load the range list point to the new copy."""
import struct
from pe import PE
import fonttable

# where the half-width pen step is, and how the renderer keeps its variables (checked against the original bytes)
HOOK = {
    "main": dict(at=0x4471e8, back=0x447209,
                 orig="8b442428992bc28bc88b842464010000992bc2d1f803442424d1f903c189442424",
                 # byte = string[ebp]: string base [esp+0x20], index ebp; size [esp+0x28]; spacing [esp+0x164]; pen [esp+0x24]
                 load="8b442420" "0fb60428",                      # mov eax,[esp+20h] ; movzx eax,byte [eax+ebp]
                 size="0faf442428",                               # imul eax,[esp+28h]
                 spacing="8b842464010000",                        # mov eax,[esp+164h]
                 pen_add="03442424", pen_store="89442424"),       # add eax,[esp+24h] ; mov [esp+24h],eax
    "special": dict(at=0x448d20, back=0x448d43,
                 orig="8b851cffffff992bc28bc88b451c992bc2d1f8038530ffffffd1f903c1898530ffffff",
                 # byte = string[index]: string base [ebp-0xd4], index [ebp-0xc8]; size [ebp-0xe4]; spacing [ebp+0x1c]; pen [ebp-0xd0]
                 load="8b852cffffff" "038538ffffff" "0fb600",     # mov eax,[ebp-d4h] ; add eax,[ebp-c8h] ; movzx eax,byte [eax]
                 size="0faf851cffffff",                           # imul eax,[ebp-e4h]
                 spacing="8b451c",                                # mov eax,[ebp+1ch]
                 pen_add="038530ffffff", pen_store="898530ffffff"),
}

def pe_checksum(b):
    pe = struct.unpack("<I", b[0x3c:0x40])[0]; co = pe + 24 + 64
    s = 0; d = bytearray(b); d[co:co + 4] = b"\0\0\0\0"
    if len(d) % 2: d += b"\0"
    for (w,) in struct.iter_unpack("<H", bytes(d)):
        s += w; s = (s & 0xFFFF) + (s >> 16)
    return (s + len(b)) & 0xFFFFFFFF

def _align(x, a): return (x + a - 1) // a * a

def patch(exe_bytes, which, extra_ranges, adv=None):
    p = PE(exe_bytes); b = bytearray(exe_bytes)
    pe = struct.unpack("<I", b[0x3c:0x40])[0]; ns = struct.unpack("<H", b[pe + 6:pe + 8])[0]
    osz = struct.unpack("<H", b[pe + 20:pe + 22])[0]; opt = pe + 24
    salign, falign = struct.unpack("<II", b[opt + 32:opt + 40]); soi = struct.unpack("<I", b[opt + 56:opt + 60])[0]
    last = max(s[3] + s[4] for s in p.sec)
    assert last == len(b), "the exe has data after its last section"
    hdr = opt + osz + 40 * ns
    assert set(b[hdr:hdr + 40]) == {0} and hdr + 40 <= min(s[3] for s in p.sec), "no room for a section header"
    rva = soi; va = p.base + rva
    tbl_va, refs = fonttable.EXES[which]
    ranges = fonttable.read_ranges(p, tbl_va) + list(extra_ranges)
    sec = bytearray(0x400)
    blob = b"".join(struct.pack("<HH", lo, hi) for lo, hi in ranges) + b"\xff\xff\xff\xff"
    assert len(blob) <= 0x200
    sec[0:len(blob)] = blob
    for r in refs:
        o = p.off(r); assert struct.unpack("<I", b[o:o + 4])[0] == tbl_va
        b[o:o + 4] = struct.pack("<I", va)
    if adv is not None:
        assert len(adv) == 256
        sec[0x200:0x300] = adv
        h = HOOK[which]; at = p.off(h["at"]); n = h["back"] - h["at"]
        assert b[at:at + n].hex() == h["orig"], "half-width pen code differs"
        cva = va + 0x300
        code = bytes.fromhex(h["load"]) + b"\x0f\xb6\x80" + struct.pack("<I", va + 0x200)   # movzx eax,byte [ADV+eax]
        code += bytes.fromhex(h["size"]) + bytes.fromhex("83c00e" "99" "b91c000000" "f7f9" "8bc8")  # add eax,14; cdq; mov ecx,28; idiv ecx; mov ecx,eax
        code += bytes.fromhex(h["spacing"]) + bytes.fromhex("992bc2d1f8")                   # cdq; sub eax,edx; sar eax,1
        code += bytes.fromhex(h["pen_add"]) + bytes.fromhex("03c1") + bytes.fromhex(h["pen_store"])  # add eax,ecx
        code += b"\xe9" + struct.pack("<i", h["back"] - (cva + len(code) + 5))             # jmp back
        sec[0x300:0x300 + len(code)] = code
        b[at:at + n] = b"\xe9" + struct.pack("<i", cva - (h["at"] + 5)) + b"\x90" * (n - 5)
    # section header ".yue": code + data, read/write/execute
    raw = _align(len(b), falign); b += b"\0" * (raw - len(b))
    hdr_bytes = b".yue\0\0\0\0" + struct.pack("<IIII", len(sec), rva, len(sec), raw) + b"\0" * 12 + struct.pack("<I", 0xE0000060)
    b[hdr:hdr + 40] = hdr_bytes
    b += bytes(sec) + b"\0" * (_align(len(sec), falign) - len(sec))
    struct.pack_into("<H", b, pe + 6, ns + 1)
    struct.pack_into("<I", b, opt + 56, _align(rva + len(sec), salign))
    struct.pack_into("<I", b, opt + 64, pe_checksum(bytes(b)))
    return bytes(b), fonttable.Table(ranges)
