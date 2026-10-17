"""Character code -> font atlas cell, exactly as WA2.exe does it (function 0x401050, range list 0x4a14b8).
cell = sum of (hi - lo + 1) over the ranges before the one holding the code + (code - lo); the atlas has 80 columns.
Ranges count the trail byte 0x7F as a cell. Single bytes 0xB1-0xDD appear sign-extended (0xFFB1-0xFFDD)."""
import struct
from pe import PE
COLS = 80
EXES = {"main": (0x4a14b8, (0x401008, 0x401053)), "special": (0x49e4b8, (0x40100b, 0x401056))}   # table VA, imm32 refs

def read_ranges(exe_bytes_or_pe, va):
    p = exe_bytes_or_pe; o = p.off(va); R = []
    while True:
        lo, hi = struct.unpack("<HH", p.b[o:o + 4]); o += 4
        if hi == 0xFFFF: return R
        R.append((lo, hi))

class Table:
    def __init__(self, ranges):
        self.ranges = list(ranges); self.cell = {}; n = 0
        for lo, hi in self.ranges:
            for c in range(lo, hi + 1): self.cell.setdefault(c, n + c - lo)
            n += hi - lo + 1
        self.total = n
    def code_cell(self, code):
        if 0x80 <= code < 0x100: code |= 0xFF00             # single-byte half-width kana, sign-extended
        return self.cell.get(code)
    def chars(self):
        """cell -> unicode char for every cell that holds a cp932 character"""
        out = {}
        for c, i in self.cell.items():
            if c >= 0xFF00: b = bytes([c & 0xFF])
            elif c < 0x100: b = bytes([c])
            else: b = struct.pack(">H", c)
            try: out[i] = b.decode("cp932")
            except UnicodeDecodeError: pass
        return out

def original(exe_path, which="main"):
    return Table(read_ranges(PE(exe_path), EXES[which][0]))
