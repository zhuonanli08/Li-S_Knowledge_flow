# -*- coding: utf-8 -*-
"""导出数据集 v2（2026-10-11）
相对 v1 的改动（用户 2026-10-11 确认）：
  1. 补池：固态锂硫 / 准固态锂硫引用了、但检索没捞到的文献（2010 年前、综述、检索式没覆盖的写法），
     用 output/fetch_cited_v2.py 拉到的元数据跑同一套分组规则；分进组的补进论文池，只作被引方，不作引用方。
     与池内论文标题相同（年份差 ≤1）的，视为同一篇的另一个编号，并到池内那篇
  2. 分组规则 v2（preflight_v3_cached.py 的 li_ok）：硫化物全固态默认算锂体系；任意「Li+数字」化学式都算提到锂
  3. 新增列：论文表加「来源」（检索 / 补池）和「文献类型」（OpenAlex 的 type；检索来的都是 article）；
     引用表加「被引方来源」「被引方文献类型」
输出 output/dataset_v2/：论文表.csv、引用表.csv、补池核对.xlsx（v1 的文件不动）
"""
import sys, io, os, re, json, csv, glob, gzip, time, random, math
from collections import Counter, defaultdict
os.chdir(r"D:\Desktop\课题一锂硫知识流动分析"); sys.path.insert(0, ".")
_b = io.StringIO(); _o = sys.stdout; sys.stdout = _b
import preflight_v3_cached as V
sys.stdout = _o
P = V.P
import requests
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
clean = lambda v: ILLEGAL_CHARACTERS_RE.sub("", v) if isinstance(v, str) else v   # 补池文献的标题摘要里有 Excel 不收的控制字符

OUT = "output/dataset_v2"; os.makedirs(OUT, exist_ok=True)
KEY = os.environ.get("OPENALEX_KEY", "")
GN = {"S-LiS": "固态锂硫", "QSS-LiS": "准固态锂硫", "L-LiS": "液态锂硫", "S-LiB": "固态锂电池"}
SUBN = {"sulfide": "硫化物", "thiolisicon": "硫化物",   # 2026-10-11 用户定：thio-LISICON 并入硫化物
        "oxide": "氧化物", "halide": "卤化物/氯化物", "hydride": "硼氢化物",
        "polymer": "聚合物", "gel": "凝胶/准固态", "insitu": "原位聚合（状态未写明）", "composite": "复合", "el?": "未标明", "other-solid": "未标明"}
RN = {"SPAN": "SPAN", "S-C": "单质硫复合", "Li2S": "Li2S 正极", "orgS": "有机硫", "route?": "未标明"}
TAG2SUB = {"el_thiolisicon": "thiolisicon", "el_sulfide": "sulfide", "el_halide": "halide", "el_hydride": "hydride",
           "el_oxide": "oxide", "el_polymer": "polymer", "el_quasi": "gel"}
short = lambda w: w.rsplit("/", 1)[-1]
full = lambda s: "https://openalex.org/" + s

def m(rx, s):
    r = rx.search(s); return r.group(0) if r else ""
def tag_match(tag, text):
    for rx in (P.RX.get(tag), V.EXTRA.get(tag)):
        if rx is not None:
            x = m(rx, text)
            if x: return x
    return ""

# ---------- 本地 PDF（全文库仍在原处） ----------
LIB = r"D:\Desktop\锂电催化\机器学习\skills\Open-Papertrail\Open-Papertrail\corpus\library"
tk = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
local = []
for d in ["05_LiS_solid-state", "02_LiS_electrolyte", "01_LiS_catalyst"]:
    for f in glob.glob(os.path.join(LIB, d, "**", "*.pdf"), recursive=True):
        b = os.path.basename(f)[:-4]
        if re.search(r"_SI(\d*)$", b, re.I): continue
        x = re.match(r"(\d{4})_[^_]*_[^_]*_(.+)$", b)
        if x: local.append((int(x.group(1)), tk(x.group(2)), os.path.relpath(f, LIB)))
loc_by = defaultdict(list)
for y, k, p in local: loc_by[k[:30]].append((y, k, p))
def find_local(year, k):
    for y, lk, p in loc_by.get(k[:30], []):
        n = min(len(lk), len(k), 60)
        if abs(y - year) <= 1 and n >= 30 and lk[:n] == k[:n]: return p
    return ""

# ---------- 一篇论文 → 论文表的一行（不进组返回 None） ----------
def make_row(wid, w, src, typ):
    t = w.get("title") or ""; ab = P.rebuild_abstract(w.get("abstract_inverted_index"))
    text = V.norm(t + " " + ab); tn = V.norm(t)
    a, b, c, f = V.classify(text, t, wid)
    if a is None: return None
    tags = V.tag_all(text)
    sub = c.split("|")[-1]; route = b.split("|")[1] if a.endswith("LiS") else None
    ev = []
    if a.endswith("LiS"): ev.append("锂硫←" + (m(V.LIS, text) or m(V.LIS_CS, text) or ("SPAN 专检" if wid in V.SPAN_IDS else "")))
    if a in ("S-LiS", "S-LiB"):
        s_ev = next((tag_match(k, text) for k in P.SOLID_KEYS + ("el_hydride", "el_thiolisicon") if tag_match(k, text)), "") or m(V.SOLID_GEN, text)
        ev.append("固态←" + s_ev)
    if a == "S-LiB" and not V.LI.search(text):
        ev.append("锂←" + (m(V.LI_V2, text) or "硫化物电解质默认锂：" + m(V.SULF_EL, text)))
    if a == "QSS-LiS": ev.append("准固态←" + tag_match("el_quasi", text))
    sub_src = ""
    if a in ("S-LiS", "QSS-LiS", "S-LiB") and sub not in ("el?", "other-solid"):
        hit = next((k for k, v in TAG2SUB.items() if v == sub and k in tags), None)
        if sub == "composite" and V.composite_hit(text): ev.append("电解质←复合：" + V.composite_hit(text)); sub_src = "摘要"
        elif hit: ev.append("电解质←" + tag_match(hit, text)); sub_src = "摘要"
        elif wid in V.FT_SUB: ev.append("电解质←全文"); sub_src = "全文"
    route_src = ""
    if route and route != "route?":
        if route == "SPAN": rv = m(V.SPAN_RX, text) or "SPAN 专检"
        elif route == "Li2S": rv = tag_match("ca_li2s", text) or m(V.ROUTE_LI2S, text)
        elif route == "orgS": rv = m(V.ROUTE_ORG, text)
        else: rv = tag_match("ca_sc", text) or tag_match("ca_ss", text) or m(V.ROUTE_SC, text)
        if rv: ev.append("路线←" + rv); route_src = "摘要"
        elif wid in V.FT_ROUTE: ev.append("路线←全文"); route_src = "全文"
    el_t = m(V.EL_TITLE, tn)
    if el_t: ev.append("标题讲电解质←" + el_t)
    return {
        "编号": short(wid), "DOI": "", "年份": w.get("publication_year") or "", "标题": t, "摘要": ab,
        "分组": GN[a],
        "电解质类型": "不适用（液态）" if a == "L-LiS" else SUBN.get(sub, sub),
        "正极路线": "不适用" if a == "S-LiB" else RN.get(route, route),
        "标题讲电解质": "是" if el_t else "否",
        "电解质来源": sub_src, "路线来源": route_src, "判定依据": "；".join(ev),
        "有摘要": "是" if ab else "否",
        "本地PDF": find_local(w.get("publication_year") or 0, tk(t)) if a.endswith("LiS") else "",
        "参考文献数": len(w.get("referenced_works") or []) if src == "检索" else "",
        "并入的重复编号": "",
        "来源": src, "文献类型": typ,
    }

# ---------- 论文表：检索来的 ----------
papers = {}
for wid, w in V.raw.items():
    p = make_row(wid, w, "检索", "article")
    if p: papers[wid] = p
V.RULES = "v1"   # 记下哪些论文因规则 v2 改了分组（含新进池、换组），供核对
v1g = {}
for wid, w in V.raw.items():
    v1g[wid] = GN.get(V.classify(V.norm((w.get("title") or "") + " " + P.rebuild_abstract(w.get("abstract_inverted_index"))), w.get("title") or "", wid)[0])
V.RULES = "v2"
rule_new = [wid for wid in V.raw if v1g[wid] != (papers[wid]["分组"] if wid in papers else None)]
for wid, p in papers.items(): p["v1 分组"] = v1g.get(wid) or "不进组"   # 数据集 v1 已删除，靠这一列追溯 v1 的分组
citing = [wid for wid, p in papers.items() if p["分组"] in ("固态锂硫", "准固态锂硫")]

# 被引次数（补池时按被引多少排序；核对表用「被固态锂硫引用次数」）
cite_all, cite_sl = Counter(), Counter()
for wid in citing:
    seen = set()
    for r in V.raw[wid].get("referenced_works") or []:
        r = V.DUP_MAP.get(r, r)
        if r in seen or r == wid: continue
        seen.add(r); cite_all[r] += 1
        if papers[wid]["分组"] == "固态锂硫": cite_sl[r] += 1

# ---------- 补池：检索没捞到的被引文献 ----------
CM = json.load(gzip.open("output/cited_meta_v2.json.gz", "rt", encoding="utf-8"))
found = {full(k): v for k, v in CM["found"].items()}
key2 = {}
for wid, p in papers.items():
    k = V._tkey(p["标题"])
    if len(k) >= 25: key2.setdefault(k, (wid, int(p["年份"] or 0)))
ALIAS, added = {}, []
for wid in sorted(found, key=lambda w: (-cite_all[w], w)):
    if wid in V.raw: continue
    x = found[wid]
    k = V._tkey(x.get("title")); y = x.get("publication_year") or 0
    if len(k) >= 25 and k in key2 and abs(key2[k][1] - y) <= 1:
        ALIAS[wid] = key2[k][0]; continue
    p = make_row(wid, x, "补池", x.get("type") or "")
    if p:
        p["DOI"] = (x.get("doi") or "").replace("https://doi.org/", ""); p["v1 分组"] = "池外（v1 未收）"
        papers[wid] = p; added.append(wid)
        if len(k) >= 25: key2.setdefault(k, (wid, y))
# ---------- 主题复核（2026-10-11 用户定「无关论文删掉」）----------
# OpenAlex 主主题不是电池类、且标题里没有本组核心词 → 判为无关论文，移出论文池（引用它的记为池外）。
# 只看主题会误删（机器学习筛电解质、硼氢化物、MOF 电解质等主题不叫电池），只看关键词会漏删，两个条件同时满足才删
TC_F = "output/topics_cache.json"
TC = json.load(open(TC_F, encoding="utf-8")) if os.path.exists(TC_F) else {}
_need = [p["编号"] for p in papers.values() if p["编号"] not in TC]
for i in range(0, len(_need), 50):
    b = _need[i:i + 50]
    res = requests.get("https://api.openalex.org/works", params={"filter": "openalex:" + "|".join(b), "per-page": 50, "select": "id,topics", "api_key": KEY}, timeout=90).json().get("results", [])
    for x in res: TC[short(x["id"])] = [[t["display_name"], t["subfield"]["display_name"], round(t.get("score") or 0, 3)] for t in (x.get("topics") or [])][:3]
    for w in b: TC.setdefault(w, [])
json.dump(TC, open(TC_F, "w", encoding="utf-8"), ensure_ascii=False)
BATT_TOPIC = re.compile(r"batter|electrolyte|ionic conductiv", re.I)
CORE_SSB = re.compile(r"solid.state (batter|electrolyte|li|lithium|ion|ionic|conduct|polymer|cell)|all.solid|solid electrolyte|solid polymer|polymer electrolyte|gel electrolyte|"
                      r"(?<![a-wyz])li\d|li\+|li\w{0,4}\(bh4|libh4|borohydride|complex hydride|garnet|llzo|llzto|argyrodite|superionic|ion(ic)?.conduct|\bpeo\b|"
                      r"poly\(ethylene oxide\)|thiophosphate|lithium (metal|anode)|li metal|interphase", re.I)
CORE_SSB_CS = re.compile(r"\b(LATP|LAGP|LiPON|LISICON|NASICON|LGPS|SSEs?|SPEs?|CPEs?)\b")   # 缩写要大写（「LaTP」是自动驾驶算法名）
CORE_LIS = re.compile(r"sul[fp]h?ur|polysulfide|li.s\b|lithium|batter|\bspan\b|li2s|li.?ion", re.I)
def topic_off(p):
    tp = TC.get(p["编号"]) or []
    if not tp or BATT_TOPIC.search(tp[0][0]): return False   # 没有主题信息的不动
    t = V.squash(V.norm(p["标题"]))
    if p["分组"] == "固态锂电池": return not (CORE_SSB.search(t) or CORE_SSB_CS.search(t))
    return not CORE_LIS.search(t)
topic_drop = {w: papers[w] for w in list(papers) if topic_off(papers[w])}
for w in topic_drop: papers.pop(w)
citing = [w for w in citing if w in papers]
added = [w for w in added if w in papers]

dups = defaultdict(list)
for d, keep in list(V.DUP_MAP.items()) + list(ALIAS.items()): dups[keep].append(short(d))
for wid, p in papers.items(): p["并入的重复编号"] = " ".join(dups.get(wid, []))

# ---------- DOI（检索来的用 v1 的缓存，新进池的补拉） ----------
cache_f = "output/doi_cache.json"
doi = json.load(open(cache_f, encoding="utf-8")) if os.path.exists(cache_f) else {}
todo = [p["编号"] for p in papers.values() if p["来源"] == "检索" and p["编号"] not in doi]
def oa(params):
    for i in range(30):
        try:
            return requests.get("https://api.openalex.org/works", params=params, timeout=60).json()
        except Exception:
            time.sleep(min(60, 5 * (i + 1)))
    print("  [跳过一批：OpenAlex 连续 30 次失败，该批 DOI 留空]", flush=True)
    return {}
for i in range(0, len(todo), 50):
    batch = todo[i:i + 50]
    res = oa({"filter": "openalex:" + "|".join(batch), "per-page": 50, "select": "id,doi", "api_key": KEY}).get("results", [])
    for r in res: doi[short(r["id"])] = (r.get("doi") or "").replace("https://doi.org/", "")
    if res:
        for b_ in batch: doi.setdefault(b_, "")
json.dump(doi, open(cache_f, "w", encoding="utf-8"))
for p in papers.values():
    if p["来源"] == "检索": p["DOI"] = doi.get(p["编号"], "")

COLS = list(next(iter(papers.values())).keys())
with open(f"{OUT}/论文表.csv", "w", encoding="utf-8-sig", newline="") as fh:
    wr = csv.DictWriter(fh, COLS); wr.writeheader()
    for p in sorted(papers.values(), key=lambda p: (p["分组"], p["来源"], -int(p["年份"] or 0))): wr.writerow(p)

# ---------- 引用表（引用方只取检索来的固态锂硫 + 准固态锂硫，和 v1 相同） ----------
ncit = 0; outpool = Counter()
def meta_of(r):
    if r in found: return found[r].get("publication_year") or "", found[r].get("type") or ""
    if r in V.raw: return V.raw[r].get("publication_year") or "", "article"
    return "", ""
with open(f"{OUT}/引用表.csv", "w", encoding="utf-8-sig", newline="") as fh:
    wr = csv.writer(fh)
    wr.writerow(["引用方编号", "引用方分组", "引用方年份", "被引方编号", "被引方分组", "被引方标题讲电解质", "被引方年份", "被引方来源", "被引方文献类型"])
    for wid in citing:
        p = papers[wid]; seen = set()
        for r in V.raw[wid].get("referenced_works") or []:
            r = V.DUP_MAP.get(r, r); r = ALIAS.get(r, r)
            if r in seen or r == wid: continue
            seen.add(r)
            q = papers.get(r)
            if q:
                wr.writerow([p["编号"], p["分组"], p["年份"], q["编号"], q["分组"], q["标题讲电解质"], q["年份"], q["来源"], q["文献类型"]])
            else:
                yr, ty = meta_of(r)
                wr.writerow([p["编号"], p["分组"], p["年份"], short(r), "池外", "", yr, "", ty])
                if p["分组"] == "固态锂硫": outpool[r] += 1
            ncit += 1

# ---------- 核对表.xlsx（唯一一张核对表；旧的 补池核对.xlsx 删掉） ----------
if os.path.exists(f"{OUT}/补池核对.xlsx"): os.remove(f"{OUT}/补池核对.xlsx")
FONT = Font(name="Arial", size=10); HFONT = Font(name="Arial", size=10, bold=True)
HFILL = PatternFill("solid", start_color="D9D9D9"); WRAP = Alignment(wrap_text=True, vertical="top")
wb = Workbook()
def sheet(name, cols, widths, rows):
    ws = wb.create_sheet(name); ws.append(cols)
    for cell in ws[1]: cell.font = HFONT; cell.fill = HFILL; cell.alignment = WRAP
    for r in rows: ws.append([clean(v) for v in r])
    for i, wdt in enumerate(widths): ws.column_dimensions[chr(65 + i)].width = wdt
    for row in ws.iter_rows(min_row=2):
        L = 0
        for cell in row:
            cell.font = FONT; cell.alignment = WRAP
            if cell.value and isinstance(cell.value, str): L = max(L, len(cell.value) / max(widths[cell.col_idx - 1], 1))   # col_idx 新旧版 openpyxl 都是整数
        ws.row_dimensions[row[0].row].height = min(200, 13 * max(1, math.ceil(L)))
        d = row[1]
        if d.value: d.hyperlink = "https://doi.org/" + d.value; d.font = Font(name="Arial", size=10, color="0563C1", underline="single")
    ws.freeze_panes = "A2"
PC = ["编号", "DOI", "年份", "文献类型", "被固态锂硫引用", "标题", "摘要（前 500 字）", "分组", "标题讲电解质", "判定依据", "你的备注"]
PW = [12, 22, 6, 9, 8, 45, 70, 10, 8, 38, 20]
def prow(wid):
    p = papers[wid]
    return [p["编号"], p["DOI"], p["年份"], p["文献类型"], cite_sl[wid], p["标题"], (p["摘要"] or "（无摘要）")[:500], p["分组"],
            p["标题讲电解质"], p["判定依据"], ""]
def rrow(wid):   # 规则改动页：多一列 v1 分组；v2 不进组的论文不在论文表里，单独拼一行
    if wid in papers: r = prow(wid)
    else:
        w = V.raw[wid]; ab = P.rebuild_abstract(w.get("abstract_inverted_index"))
        r = [short(wid), "", w.get("publication_year") or "", "article", cite_sl[wid], w.get("title") or "", (ab or "（无摘要）")[:500], "不进组", "", "", ""]
    return r[:8] + [v1g[wid] or "不进组"] + r[8:]
# 准确率抽样：按引用加权（每条引用等概率，被引多的论文更容易抽到），从固态锂硫的池内引用里抽 200 条。
# 用「引用方+被引方」编号的哈希值排序取前 200，而不是 random.sample——规则微调后重跑，抽到的引用基本不变，已核对的不用重核
import hashlib
inpool_refs = []
for wid in citing:
    if papers[wid]["分组"] != "固态锂硫": continue
    seen = set()
    for r in V.raw[wid].get("referenced_works") or []:
        r = V.DUP_MAP.get(r, r); r = ALIAS.get(r, r)
        if r in seen or r == wid: continue
        seen.add(r)
        if r in papers: inpool_refs.append((hashlib.md5((short(wid) + short(r)).encode()).hexdigest(), r))
audit = [r for _, r in sorted(inpool_refs)[:200]]
info = wb.active; info.title = "说明"
n_add = Counter(papers[w]["分组"] for w in added)
for line in ["数据集 v2 核对表（2026-10-11；唯一一张核对表，取代 补池核对.xlsx）",
             f"补池：固态锂硫/准固态锂硫引用了、但检索没捞到的文献 {len(found):,} 篇（另 {len(CM['missing']):,} 篇 OpenAlex 查不到元数据），用同一套规则分组，"
             f"分进组的 {len(added):,} 篇补进池（{dict(n_add)}）；与池内论文同名的另一个编号 {len(ALIAS):,} 个并到池内那篇。",
             f"规则改动：v2 补了几处漏判（硫化物全固态和无摘要的固态电池标题默认算锂体系、固态锂电池补认 superionic conductor、锂硫补认标题里的老写法），"
             f"检索缓存里分组因此改变的 {len(rule_new):,} 篇见「规则改动」页（有一列 v1 分组）。",
             "前三页按「被固态锂硫引用次数」从多到少排。被引多的分错了影响大，只看前面几十行即可；分错的在「你的备注」写一句。",
             "「判定依据」= 规则命中的原文词；「锂←…」= 规则 v2 新增的锂体系判断。",
             f"主题排除页：OpenAlex 主主题不是电池类、标题里也没有本组核心词的 {len(topic_drop):,} 篇，判为无关论文移出论文池（引用它们的记为池外）；按被引次数排，可复查误删。",
             "仍在池外页：补池后固态锂硫引用最多的池外文献，看看还有没有本该进组的。",
             "准确率抽样页：从固态锂硫落在池内的参考文献里按引用加权随机抽 200 条，逐条核对分组和「标题讲电解质」，用来估计规则的准确率。",
             f"完整数据：论文表.csv（{len(papers):,} 行）、引用表.csv（{ncit:,} 行）。"]:
    info.append([line])
info.column_dimensions["A"].width = 140
for row in info.iter_rows():
    for cell in row: cell.font = FONT
info["A1"].font = HFONT
sheet(f"补池·{len(added)}篇", PC, PW, [prow(w) for w in sorted(added, key=lambda w: (-cite_sl[w], w))])
sheet(f"规则改动·{len(rule_new)}篇", PC[:8] + ["v1 分组"] + PC[8:], PW[:8] + [10] + PW[8:],
      [rrow(w) for w in sorted(rule_new, key=lambda w: (-cite_sl[w], w))])
sheet(f"主题排除·{len(topic_drop)}篇", ["编号", "DOI", "年份", "原分组", "被固态锂硫引用", "标题", "OpenAlex 主主题", "你的备注"], [12, 22, 6, 10, 8, 70, 40, 20],
      [[p["编号"], p["DOI"] or doi.get(p["编号"], ""), p["年份"], p["分组"], cite_sl[w], p["标题"], (TC.get(p["编号"]) or [[""]])[0][0], ""]
       for w, p in sorted(topic_drop.items(), key=lambda z: (-cite_sl[z[0]], z[0]))])
def why(r):
    if r in found: return "补池规则没分进任何组"
    if r in V.raw: return "检索到了，规则没分进任何组"
    return "OpenAlex 查不到元数据"
def orow(r):
    x = found.get(r) or V.raw.get(r) or {}
    return [short(r), (x.get("doi") or "").replace("https://doi.org/", ""), x.get("publication_year") or "",
            (x.get("type") or "article") if x else "", outpool[r], x.get("title") or "", why(r), ""]
sheet("仍在池外·被引最多100", ["编号", "DOI", "年份", "文献类型", "被固态锂硫引用", "标题", "为什么不在池里", "你的备注"],
      [12, 22, 6, 9, 8, 60, 22, 20], [orow(r) for r, _ in outpool.most_common(100)])
sheet("准确率抽样·200条", ["编号", "DOI", "年份", "文献类型", "被固态锂硫引用", "标题", "摘要（前 500 字）", "分组", "标题讲电解质", "判定依据", "核对：分组", "核对：讲电解质", "核对说明"],
      [12, 22, 6, 9, 8, 45, 60, 10, 8, 30, 10, 10, 30], [prow(w)[:10] + ["", "", ""] for w in audit])
wb.save(f"{OUT}/核对表.xlsx")

cg = Counter((p["分组"], p["来源"]) for p in papers.values())
print("论文表", len(papers), dict(cg))
print("主题排除", len(topic_drop), dict(Counter(p["分组"] for p in topic_drop.values())))
print("补池", len(added), dict(n_add), "| 同名并入", len(ALIAS), "| 规则改动", len(rule_new), Counter((v1g[w], papers[w]["分组"] if w in papers else None) for w in rule_new))
print("引用表", ncit, "| 固态锂硫的池外引用", sum(outpool.values()), "| DOI 缺失(检索来的)", sum(1 for p in papers.values() if p["来源"] == "检索" and not p["DOI"]))
