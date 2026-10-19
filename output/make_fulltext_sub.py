# -*- coding: utf-8 -*-
"""本地有全文、但标题摘要认不出「电解质类型」或「正极路线」的固态锂硫论文：读全文正文判断。
输出 output/fulltext_labels.json  {"sub": {wid: 电解质}, "route": {wid: 路线}}（供 preflight_v3_cached.py 使用）
     output/全文补判_核对表.md
规则：某类在正文（去参考文献，前 12 页）出现 >=3 次，且至少是第二名的 2 倍 → 判为该类；两类相当或都不足 → 不判
（2026-10-11：thio-LISICON 并入硫化物一起数；两类相当不再记「复合」，复合电解质按用户定义另判）
"""
import sys, io, os, re, glob, json
from collections import Counter
os.chdir(r"D:\Desktop\课题一锂硫知识流动分析")
sys.path.insert(0, ".")
if os.path.exists("output/fulltext_labels.json"): os.remove("output/fulltext_labels.json")   # 重新生成，避免用到旧结果
_b = io.StringIO(); _o = sys.stdout; sys.stdout = _b
import preflight_v3_cached as V
sys.stdout = _o
P = V.P
import pymupdf

LIB = r"D:\Desktop\锂电催化\机器学习\skills\Open-Papertrail\Open-Papertrail\corpus\library"   # 全文库仍在原处（下载任务共用）
def key(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())
local = []
for d in ["05_LiS_solid-state", "02_LiS_electrolyte", "01_LiS_catalyst"]:
    for f in glob.glob(os.path.join(LIB, d, "**", "*.pdf"), recursive=True):
        b = os.path.basename(f)[:-4]
        if re.search(r"_SI(\d*)$", b, re.I): continue
        m = re.match(r"(\d{4})_[^_]*_[^_]*_(.+)$", b)
        if m: local.append(dict(year=int(m.group(1)), tk=key(m.group(2)), path=f))
def find_local(year, tk):
    for lc in local:
        n = min(len(lc["tk"]), len(tk), 60)
        if abs(lc["year"] - year) <= 1 and n >= 30 and lc["tk"][:n] == tk[:n]: return lc["path"]

EL = {
    "sulfide": r"thio.?LISICON|Li3\.25Ge|Li4GeS4|Li4-xGe1-xPxS4|Li3\.4Si0\.4P0\.6S4|Li3\.33Ge|Li6PS5(Cl|Br|I)|Li[0-9.]+PS[0-9.]+(Cl|Br|I)|Li3PS4|Li10GeP2S12|\bLGPS\b|Li7P3S11|argyrodite|thiophosphate|"
               r"Li2S-P2S5|sulfide[- ](solid[- ])?(state )?electrolyte|Li4SnS4|Li9\.54Si1\.74|\b(75|70|80)Li2S",
    "halide": r"Li3InCl6|Li3YCl6|Li3YBr6|Li2ZrCl6|Li3ScCl6|LiAlCl4|Li3ErCl6|Li3HoCl6|LiTaOCl|"
              r"halide[- ](solid[- ])?(state )?electrolyte|chloride[- ](solid[- ])?(state )?electrolyte|oxychloride",
    "hydride": r"LiBH4|Li4\(BH4\)3I|borohydride|complex hydride|closo|Li2B12H12|LiCB11",
    "oxide": r"Li7La3Zr2O12|\bLLZO\b|\bLLZTO\b|\bLLTO\b|\bLATP\b|\bLAGP\b|garnet|NASICON|\bLiPON\b|Li1\.3Al0\.3Ti1\.7|Li1\.5Al0\.5Ge1\.5|Li6\.4La3|Li6\.75La3",
    "polymer": r"\bPEO\b|poly\(ethylene oxide\)|polymer electrolyte|\bSPEs?\b|\bPPC\b|poly\(propylene carbonate\)|PVDF-HFP|\bPEGDA\b|\bPEGDME\b|single[- ]ion conduct",
    "gel": r"gel polymer electrolyte|\bGPE\b|gel electrolyte|in[- ]?situ polymeri[sz]|\bPDOL\b|poly\(1,3-dioxolane\)|quasi[- ]solid",
}
ROUTE = {
    "SPAN": r"sulfurized polyacrylonitrile|\bSPAN\b|S@pPAN|sulfur/polyacrylonitrile|sulfurized PAN",
    "Li2S": r"Li2S (cathode|electrode|positive)|Li2S-based (cathode|composite|electrode|positive)|Li2S composite|Li2S@|Li2S/C\b|Li2S-C\b|nano-?Li2S|Li2S nanoparticle",
    "orgS": r"organosulfur|organo-sulfur|sulfur-rich (polymer|copolymer)|inverse vulcani[sz]|sulfur copolymer",
    "S-C": r"sulfur[- /]carbon|\bS/C\b|S-C composite|\bS/KB\b|\bS-KB\b|Ketjen|elemental sulfur|\bS8\b|sublimed sulfur|sulfur powder|"
           r"\bS/AB\b|\bS/CNT\b|sulfur composite cathode|sulfur/VGCF|S/VGCF|sulfur-carbon",
}
EL = {k: re.compile(v) for k, v in EL.items()}
ROUTE = {k: re.compile(v) for k, v in ROUTE.items()}
LAB = {"thiolisicon": "thio-LISICON", "sulfide": "硫化物", "halide": "卤化物/氯化物", "hydride": "硼氢化物",
       "oxide": "氧化物", "polymer": "聚合物", "gel": "凝胶/准固态", "composite": "复合（两类相当）",
       "SPAN": "SPAN", "Li2S": "Li2S 正极", "orgS": "有机硫", "S-C": "单质硫复合"}

def body_text(path, max_pages=12):
    try:
        doc = pymupdf.open(path)
        txt = "\n".join(doc[i].get_text() for i in range(min(len(doc), max_pages)))
    except Exception:
        return None
    cut = max(txt.rfind("\nReferences"), txt.rfind("\nREFERENCES"), txt.rfind("\nReference\n"))
    txt = txt[:cut] if cut > len(txt) * 0.4 else txt
    # 拼回被拆开的化学式下标：「Li 6 PS 5 Cl」→「Li6PS5Cl」
    txt = re.sub(r"(?<=[A-Za-z)])\s+(?=[0-9.]+\s*[A-Z(])", "", txt)
    txt = re.sub(r"(?<=[0-9.])\s+(?=[A-Z][a-z]?[0-9A-Z(])", "", txt)
    return txt

def decide(cnt, allow_composite):
    top = sorted(((k, v) for k, v in cnt.items() if v), key=lambda x: -x[1])
    if not top or top[0][1] < 3: return None
    if len(top) == 1 or top[0][1] >= 2 * top[1][1]: return top[0][0]
    return "composite" if allow_composite else None

out = {"sub": {}, "route": {}}; rows = []
for wid, w in V.raw.items():
    t = w.get("title") or ""
    text = V.norm(t + " " + P.rebuild_abstract(w.get("abstract_inverted_index")))
    a, b, c, f = V.classify(text, t, wid)
    if a != "S-LiS": continue
    need_sub, need_route = c.endswith("|el?"), b.endswith("|route?")
    if not (need_sub or need_route): continue
    path = find_local(w.get("publication_year") or 0, key(t))
    if not path: continue
    txt = body_text(path)
    if txt is None: rows.append((t, "PDF 读不出", "", "")); continue
    vs = vr = "—"
    if need_sub:
        ce = {k: len(rx.findall(txt)) for k, rx in EL.items()}
        s = decide(ce, False)
        if s: out["sub"][wid] = s
        vs = LAB.get(s, "全文也判不出")
    if need_route:
        cr = {k: len(rx.findall(txt)) for k, rx in ROUTE.items()}
        r = decide(cr, False)
        if r: out["route"][wid] = r
        vr = LAB.get(r, "全文也判不出")
    rows.append((t, vs, vr, ""))

json.dump(out, open("output/fulltext_labels.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
L = ["# 全文补判：核对表\n", f"对象：本地有全文、标题摘要认不出电解质类型或正极路线的固态锂硫论文，共 {len(rows)} 篇（「—」= 摘要已能判断，无需补）。\n",
     "规则：某类在正文（去参考文献，前 12 页）出现 ≥3 次且至少是第二名的 2 倍 → 判为该类；否则不判。\n"]
L.append("电解质：" + "；".join(f"{k} {v}" for k, v in Counter(r[1] for r in rows if r[1] != "—").most_common()))
L.append("\n路线：" + "；".join(f"{k} {v}" for k, v in Counter(r[2] for r in rows if r[2] != "—").most_common()))
L.append("\n| 标题 | 电解质（全文） | 路线（全文） |\n|---|---|---|")
L += [f"| {t} | {s} | {r} |" for t, s, r, _ in sorted(rows, key=lambda r: (r[1], r[2]))]
open("output/全文补判_核对表.md", "w", encoding="utf-8").write("\n".join(L))
print("补判对象", len(rows), "| 电解质:", dict(Counter(r[1] for r in rows if r[1] != "—")), "| 路线:", dict(Counter(r[2] for r in rows if r[2] != "—")))
