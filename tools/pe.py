"""Tiny PE helper for WA2.exe analysis: file offset <-> VA, xref search, disassembly (capstone)."""
import struct, re, capstone
class PE:
    def __init__(s, path):
        s.b = bytes(path) if isinstance(path, (bytes, bytearray)) else open(path, "rb").read(); b = s.b
        pe = struct.unpack("<I", b[0x3c:0x40])[0]; ns = struct.unpack("<H", b[pe+6:pe+8])[0]; osz = struct.unpack("<H", b[pe+20:pe+22])[0]
        s.base = struct.unpack("<I", b[pe+52:pe+56])[0]; s.sec = []
        so = pe + 24 + osz
        for i in range(ns):
            e = b[so+40*i:so+40*i+40]; vs, va, rs, ro = struct.unpack("<IIII", e[8:24])
            s.sec.append((e[:8].rstrip(b"\0").decode(), va, vs, ro, rs))
        s.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    def va(s, off):
        for n, va, vs, ro, rs in s.sec:
            if ro <= off < ro + rs: return s.base + va + off - ro
    def off(s, va):
        r = va - s.base
        for n, v, vs, ro, rs in s.sec:
            if v <= r < v + max(vs, rs): return ro + r - v
    def xref(s, va):           # absolute 32-bit references to va
        return [s.va(m.start()) for m in re.finditer(re.escape(struct.pack("<I", va)), s.b)]
    def calls(s, va):          # E8 rel32 calls to va
        out = []; t = s.sec[0]; lo = t[3]; hi = t[3] + t[4]
        for i in range(lo, hi - 5):
            if s.b[i] == 0xE8 and (s.va(i) + 5 + struct.unpack("<i", s.b[i+1:i+5])[0]) & 0xffffffff == va: out.append(s.va(i))
        return out
    def dis(s, va, n=40, size=0x400):
        o = s.off(va); out = []
        for ins in s.md.disasm(s.b[o:o+size], va):
            out.append("%08x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
            if len(out) >= n: break
        return "\n".join(out)
