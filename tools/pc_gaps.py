"""Lines the direct alignment (run_ic.py + make_map.py) left untranslated, with the subtitle cues that sit in the same
gap of the alignment, for review. Nothing here goes into the game until it is approved (notes/review_*.tsv).
   python tools/pc_gaps.py   -> work/gaps.pkl, work/gaps_report.md
A gap = the stretch between two matched (cue, line) pairs. When a gap has as many leftover cues as untranslated lines,
they are paired in order ("pair"); otherwise both sides are listed ("list"). Pairs the alignment found but rejected
because the neighbourhood scored low (make_map's "diverged" check) are listed too ("diverged")."""
import os, sys, pickle, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
G, res = pickle.load(open(paths.ALIGN_PKL, "rb"))
_, TMAP, UNM, DIV = pickle.load(open(paths.MAP_PKL, "rb"))
done = lambda g: G[g][1] in TMAP.get(G[g][0], {})
# 1012_030_2 repeats the second half of 1012_030 line for line (scene replay): not a gap
REPLAY = {"1012_030_2"}
# scenes the subtitle videos do not show (checked by hand): never propose cues for them
NOT_IN_SUBS = {"1008_020", "1010_020"}   # Chiaki's scenes
divset = {(f, g) for f, _, g in DIV}
# overlay chatter in the subtitles (Io/Takeya... during the ep07 concert) is not in any PC script (.txt or .bnr)
NAMED = ("Io", "Takeya", "JK", "Tomo", "Takahiro", "Akina")
gaps = []
for f, r in res.items():
    A, pairs = r["A"], r["pairs"]
    ep = re.search(r"- (\d+)\.ass", f).group(1)
    cur_a, cur_g, prev = [], [], None
    def flush(nxt):
        ga = [g for g in cur_g if not done(g) and G[g][0] not in REPLAY and G[g][0] not in NOT_IN_SUBS]
        if ga or cur_a:
            if ga: gaps.append(dict(ep=ep, cues=[A[a]["text"] for a in cur_a], cue_ids=list(cur_a), lines=ga, prev=prev, next=nxt))
    for a, g in pairs:
        if a is not None and g is not None and (f, g) not in divset and done(g):
            flush(g); cur_a, cur_g, prev = [], [], g
        else:
            if a is not None and A[a]["style"] not in NAMED: cur_a.append(a)
            if g is not None: cur_g.append(g)
    flush(None)
# inside each gap: local alignment of the leftover cues against the untranslated lines -> proposals with a score
from align import feats, align_fast
for x in gaps:
    x["kind"] = "pair" if len(x["cues"]) == len(x["lines"]) else "list"
    x["prop"] = []
    if x["cues"]:
        pr, S0 = align_fast(feats(x["cues"], False), feats([G[g][2] for g in x["lines"]], True), gap=-0.8)
        x["prop"] = [(x["lines"][g], x["cues"][a], float(S0[a, g])) for a, g in pr if a is not None and g is not None]
pickle.dump(gaps, open(os.path.join(paths.WORK, "gaps.pkl"), "wb"))
left = [j for j in range(len(G)) if not done(j) and G[j][0] not in REPLAY]
ing = {g for x in gaps for g in x["lines"]}
out = ["# 对齐后仍是日文的句子（PC）", "",
       "共 %d 句；在缺口里有字幕可配的 %d 句（%d 个缺口，其中数量相等可按顺序配的 %d 个）；其余 %d 句附近没有剩余字幕。" % (
           len(left), len(ing), len(gaps), sum(x["kind"] == "pair" for x in gaps), len(left) - len(ing)), ""]
for x in gaps:
    out.append("## 第 %s 集  %s  前一句 %s" % (x["ep"], x["kind"], "%s #%d" % G[x["prev"]][:2] if x["prev"] is not None else "-"))
    for g in x["lines"]: out.append("- 游戏 %s #%d：%s" % (G[g][0], G[g][1], G[g][2].replace("\\n", "／")))
    for c in x["cues"]: out.append("- 字幕：%s" % c.replace("\n", "／"))
    if x["prop"]:
        out += ["", "局部对齐建议（分数越高越可信）："]
        for g, c, sc in x["prop"]:
            out.append("- %.2f  %s #%d：%s  →  %s" % (sc, G[g][0], G[g][1], G[g][2].replace("\\n", "／"), c.replace("\n", "／")))
    out.append("")
out.append("## 附近没有剩余字幕的句子")
for j in left:
    if j not in ing: out.append("- %s #%d：%s" % (G[j][0], G[j][1], G[j][2].replace("\\n", "／")))
open(os.path.join(paths.WORK, "gaps_report.md"), "w", encoding="utf-8").write("\n".join(out))
print("untranslated", len(left), "in gaps with cues", len(ing), "gaps", len(gaps), "pairable", sum(x["kind"] == "pair" for x in gaps))
# proposals: gap-local alignment above + 2nd-run pairs that make_map rejected for a low neighbourhood score
from align import ass_lines
A2 = [x for x in ass_lines(os.path.join(paths.ASS_DIR, "White Album 2 (ic) 2nd run.ass")) if not x["style"].startswith(("Prologue", "Lyric", "Note", "Episode"))]
PROP = {}
for x in gaps:
    for g, c, sc in x["prop"]: PROP.setdefault(g, []).append(("缺口", c, sc))
for a, g, sc, w in pickle.load(open(os.path.join(paths.WORK, "second_run_pairs.pkl"), "rb")):
    if a is not None and g is not None and not done(g) and G[g][0] not in REPLAY and G[g][0] not in NOT_IN_SUBS:
        PROP.setdefault(g, []).append(("2nd run", A2[a]["text"], sc))
pickle.dump(PROP, open(os.path.join(paths.WORK, "proposals.pkl"), "wb"))
# review table: my first judgement in column 1, the user's decision goes in column 2 (采用 / 不采用)
def ell(t): return re.fullmatch(r"[「」…]+", t) is not None
rows = ["	".join(["初判", "你的决定", "来源", "分数", "脚本", "字段", "日文", "字幕（建议）"])]
for g in list(PROP):                                   # same cue from both sources -> one row
    seen = {}
    for src, c, sc in PROP[g]:
        if c in seen: seen[c] = (seen[c][0] + "+" + src, c, max(sc, seen[c][2]))
        else: seen[c] = (src, c, sc)
    PROP[g] = list(seen.values())
pickle.dump(PROP, open(os.path.join(paths.WORK, "proposals.pkl"), "wb"))
for g in sorted(PROP):
    n, i, t = G[g]
    for src, c, sc in PROP[g]:
        if ell(t) and ell(c) and (t[:1] == "「") != (c[:1] == "「"): v = "不采用（括号不同的省略号，多半是别处的）"
        elif len({cc for _, cc, _ in PROP[g]}) > 1: v = "二选一"
        elif sc >= 0.6: v = "建议采用"
        else: v = "待定（分数低，多半是括号不同或拟声）"
        rows.append("	".join([v, "", src, "%.2f" % sc, n, str(i), t, c.replace(chr(10), "\\n")]))
open(os.path.join(paths.ROOT, "notes", "review_gaps.tsv"), "w", encoding="utf-8-sig").write(chr(10).join(rows) + chr(10))
print("lines with proposals", len(PROP), "rows", len(rows) - 1)
