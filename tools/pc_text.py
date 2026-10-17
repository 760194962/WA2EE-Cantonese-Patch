"""Final Cantonese text for the PC scripts, straight from the subtitles.
Sources: the direct alignment (run_ic.py + make_map.py), lines of notes/review_gaps.tsv marked 采用 in column 2,
1012_030_2 (a replay of the second half of 1012_030, line for line), the side story pages (novel_map.py) and the
speaker names. Text rules as in the PS3 build: lines split over two fields with \\k, RUBY_FIX, re-breaking to 27 cells.
   python tools/pc_text.py  -> work/pc_text.pkl {script: {field: text}}, work/pc_text_report.md"""
import os, sys, re, pickle, difflib, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths, halfwidth
from scr import lines as scr_lines, load as scr_load
G, TMAP, UNM, DIV = pickle.load(open(paths.MAP_PKL, "rb"))
TMAP = {n: dict(m) for n, m in TMAP.items()}

# ---- approved review rows ----
REVIEW = os.path.join(paths.ROOT, "notes", "review_gaps.tsv")
approved = 0
if os.path.exists(REVIEW):
    for r in csv.reader(open(REVIEW, encoding="utf-8-sig"), delimiter="\t"):
        if len(r) >= 8 and r[1].strip() == "采用":
            n, i, jp, t = r[4], int(r[5]), r[6], r[7].replace("\\n", "\n")
            assert scr_load(n)[i] == jp, ("review row does not match the script", n, i)
            TMAP.setdefault(n, {})[i] = t; approved += 1

# ---- 1012_030_2 = 1012_030 from the line where it starts ----
a = scr_lines("1012_030"); b = scr_lines("1012_030_2")
sm = difflib.SequenceMatcher(None, [t for _, t in a], [t for _, t in b], autojunk=False)
rep = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag != "equal": continue
    for k in range(i2 - i1):
        ia, ib = a[i1 + k][0], b[j1 + k][0]
        if ia in TMAP.get("1012_030", {}): TMAP.setdefault("1012_030_2", {})[ib] = TMAP["1012_030"][ia]; rep += 1

def clean(t):
    return "\n".join(l for l in t.split("\n") if l.strip(" 　"))
# translator's "（…）" notes that correspond to ruby (<Rbase|ruby>) in the Japanese script
RUBY_FIX = [("呢一度（機場）", "<R機場|呢一度>"), ("我哋（欖球部）", "<R欖球部|我哋>"),
            ("高三辛班（音樂部）", "<R高三辛班|音樂部>"), ("撚(彈)", "<R彈|撚>")]
plans = {}
for name in sorted(TMAP):
    tm = TMAP[name]; fields = scr_load(name)
    idxs = [i for i, _ in scr_lines(name)]; pos_ = {i: k for k, i in enumerate(idxs)}
    m = {}; done = set()
    for i in idxs:
        if i not in tm or i in done: continue
        if fields[i].endswith("\\k\\n"):              # the Japanese splits one sentence over two fields
            k = pos_[i]
            if k + 1 >= len(idxs) or idxs[k + 1] not in tm: continue
            nx = idxs[k + 1]
            ta = clean(tm[i]).split("\n"); tbb = clean(tm[nx]).split("\n")
            rest = tbb[len(ta):] if len(tbb) > len(ta) else tbb[-1:]
            m[i] = "\\n".join(ta) + "\\k\\n"; m[nx] = "\\n".join(rest); done.add(nx)
        else:
            m[i] = clean(tm[i]).replace("\n", "\\n")
    for i in m:
        for x, y in RUBY_FIX: m[i] = m[i].replace(x, y)
    plans[name] = m

# speaker names -> Cantonese/HK forms (names follow the subtitle translation, e.g. かずさ=和紗)
SPEAKER_MAP = {
    "かずさ": "和紗", "隣席の女子生徒": "鄰座女同學", "雪菜の母": "雪菜媽媽", "雪菜の父": "雪菜爸爸",
    "諏訪先生": "諏訪老師", "男子生徒１": "男同學１", "男子生徒２": "男同學２", "男子生徒３": "男同學３",
    "女子生徒１": "女同學１", "女子生徒２": "女同學２", "女子生徒３": "女同學３", "担任教師": "班主任",
    "軽音部員": "輕音部部員", "女性教師１": "女老師１", "指導部長": "訓導主任", "車内アナウンス": "車廂廣播",
    "駅アナウンス": "車站廣播", "女性司会": "女司儀", "実行委員": "執行委員", "医師": "醫生", "女性": "女人",
    "演劇部員１": "話劇社社員１", "演劇部員２": "話劇社社員２", "演劇部員３": "話劇社社員３",
    "Ａ組担任": "甲班班主任", "男性教師": "男老師", "携帯アナウンス": "電話錄音", "大学生１": "大學生１",
    "大学生２": "大學生２", "教頭": "副校長", "コンビニ店員": "便利店店員", "ウェイトレス": "女侍應",
    "春希＆かずさ": "春希＆和紗", "かずさ＆春希": "和紗＆春希", "かずさ・雪菜": "和紗・雪菜",
    "雪菜の母＆孝宏": "雪菜媽媽＆孝宏", "ラジオの天気予報": "電台天氣報告",
}
IC_CHAIN = "1001 1002 1003 1004 1005 1006 1007 1008 1008_020 1008_030 1008_040 1008_050 1009 1009_020 1009_030 1010 1010_020 1010_030 1010_040 1010_050 1010_060 1010_070 1011 1011_020 1011_030 1012 1012_020 1012_030 1012_030_2 1013".split()
for name in IC_CHAIN:
    m = plans.setdefault(name, {})
    for i, f in enumerate(scr_load(name)):
        if i not in m and f in SPEAKER_MAP: m[i] = SPEAKER_MAP[f]

# ---- re-break lines wider than the window (27 full-width cells, like the Japanese) ----
WRAP, MAXL = 27, 4
_BRK = set("，。！？、…）」』》～︰：；")      # may end a line, must not start one
_OPEN = set("「『（《")                        # must not end a line
_PART = set("㗎嘅啦呀喎囉嘞咩喇吖噃嘛啫咋㖞嗎")    # Cantonese sentence-final particles: never start a line
_UNIT = re.compile(r"<R[^>]*>|<[^>]*>|\\[nk]|.")
def _uw(u):
    if u.startswith("<R"): return sum(_uw(c) for c in u[2:u.index("|")])
    if u.startswith("<") or u.startswith("\\"): return 0
    if ord(u) < 0x80: return halfwidth.width(u)
    if u in ("ü", "ó"): return halfwidth.width({"ü": "#", "ó": "]"}[u])
    return 1
def _wrap(line):
    out = []; us = _UNIT.findall(line)
    while sum(map(_uw, us)) > WRAP + 0.01:
        acc = 0; best = None
        for k, u in enumerate(us):
            acc += _uw(u)
            if acc > WRAP + 0.01: break
            if u in _BRK and k + 1 < len(us) and acc >= WRAP / 2: best = k + 1
        if best is None:
            best = k
            while best > 1 and us[best] in _BRK: best -= 1
        out.append("".join(us[:best])); us = us[best:]
    out.append("".join(us))
    return "\\n".join(out)
def _reflow(t):
    tail = ""
    if t.endswith("\\k\\n"): t, tail = t[:-4], "\\k\\n"
    if "\\k" in t: return None
    us, orig = [], set()
    for u in _UNIT.findall(t):
        if u == "\\n": orig.add(len(us))
        else: us.append(u)
    N = len(us); wid = [0.0]
    for u in us: wid.append(wid[-1] + _uw(u))
    def ok(p, mid):
        a, b = us[p - 1], us[p]
        if b in _BRK or b in _PART or a in _OPEN: return False
        if not mid and a not in _BRK: return False
        return not (len(a) == len(b) == 1 and a.isascii() and b.isascii() and a.isalnum() and b.isalnum())
    def cost(p): return (0 if us[p - 1] in _BRK else 3) - (1 if p in orig else 0)
    for L, mid in [(L_, m_) for L_ in range(t.count("\\n") + 1, MAXL + 1) for m_ in (False, True)]:
        dp = {0: (0.0, [])}
        for _ in range(L - 1):
            nd = {}
            for s, (c, br) in dp.items():
                for p in range(s + 1, N):
                    if wid[p] - wid[s] > WRAP + 0.01: break
                    if not ok(p, mid): continue
                    cc = c + cost(p) + (WRAP - (wid[p] - wid[s])) * 0.01
                    if p not in nd or cc < nd[p][0]: nd[p] = (cc, br + [p])
            dp = nd
        fits = [(c, br) for s, (c, br) in dp.items() if wid[N] - wid[s] <= WRAP + 0.01]
        if fits:
            cuts = [0] + min(fits)[1] + [N]
            return "\\n".join("".join(us[a:b]) for a, b in zip(cuts, cuts[1:])) + tail
    return None
WRAPPED = []
for name, m in plans.items():
    for i, t in list(m.items()):
        if all(sum(map(_uw, _UNIT.findall(ln))) <= WRAP + 0.01 for ln in t.split("\\n")): continue
        nt = _reflow(t) or "\\n".join(_wrap(ln) for ln in t.split("\\n"))
        m[i] = nt; WRAPPED.append((name, i, t.count("\\n") + 1, nt.count("\\n") + 1))

# ---- side story (digital novel 5000-5004): whole pages, wrapped by the engine ----
NOVEL = pickle.load(open(os.path.join(paths.WORK, "novel_map.pkl"), "rb"))
for name, pages in NOVEL.items(): plans[name] = dict(pages)

plans = {n: m for n, m in plans.items() if m}
pickle.dump(plans, open(os.path.join(paths.WORK, "pc_text.pkl"), "wb"))
tot = sum(len(scr_lines(n)) for n in IC_CHAIN)
txt = sum(1 for n in IC_CHAIN for i, _ in scr_lines(n) if i in plans.get(n, {}))
rep_ = ["# PC 文本", "",
        "IC 台词 %d 句，已换成粤文 %d 句（审查表采用 %d 句，1012_030_2 照搬 %d 句）；外传 %d 页。" % (
            tot, txt, approved, rep, sum(len(v) for v in NOVEL.values())),
        "重新断行 %d 句：保持行数 %d，增加行数 %d；超过 3 行的（日文最多 3 行，要在游戏里确认）：" % (
            len(WRAPPED), sum(a == b for _, _, a, b in WRAPPED), sum(b > a for _, _, a, b in WRAPPED)), ""]
for n, i, a_, b_ in WRAPPED:
    if b_ > 3: rep_.append("- %s #%d：%d → %d 行  %s" % (n, i, a_, b_, plans[n][i].replace("\\n", "／")))
open(os.path.join(paths.WORK, "pc_text_report.md"), "w", encoding="utf-8").write("\n".join(rep_) + "\n")
print("\n".join(rep_[:4]))
