#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pre-flight v2 —— 分层颗粒度体检
====================================================================
解决的问题：「电解质要分多细？正极要不要考虑？分细了数据量够不够？」

设计原则（关键）：
    节点(node)   = 网络实体，决定拓扑，数据量敏感  → 少而稳
    属性(attr)   = 挂在节点上的标签，可事后聚合    → 多而细

    所以：抽取时分到最细，建网时用粗节点，分析时按属性切片。
    粗分类不可逆（丢信息），细标注可逆（随时能聚合）。
    → 颗粒度的决定权推迟到「看到数据之后」，不需要现在拍板。

做法：
    一次宽检索 → 本地多层标注 → 同时输出 L1/L2/L3 三个层级的
    节点规模 + 跨节点引文边数，直接告诉你「能跑到多细」。

用法：
    set OPENALEX_KEY=...        (CMD)
    $env:OPENALEX_KEY="..."     (PowerShell)
    python preflight_v2_layered.py
"""

import os
import re
import sys
import json
import time
from collections import defaultdict, Counter

import requests

API = "https://api.openalex.org/works"
KEY = os.environ.get("OPENALEX_KEY", "").strip()
MAILTO = os.environ.get("OPENALEX_MAILTO", "").strip()
YEAR_FROM = 2010

if not KEY:
    sys.exit("请先设置 OPENALEX_KEY（免费申请：https://openalex.org/）")


# ==================================================================
# 1. 宽检索：只负责「把相关文献捞进来」，不负责分类
# ==================================================================
WIDE_QUERIES = {
    "LiS": ('"lithium sulfur battery" OR "lithium-sulfur batteries" OR "Li-S battery" '
            'OR "lithium sulphur battery" OR "sulfurized polyacrylonitrile" '
            'OR "Li2S cathode" OR "lithium-sulfur cell"'),
    "SSB": ('"all-solid-state lithium battery" OR "solid-state lithium-ion battery" '
            'OR "sulfide solid electrolyte" OR "garnet solid electrolyte" '
            'OR "argyrodite" OR "halide solid electrolyte" OR "LLZO" '
            'OR "solid polymer electrolyte" OR "composite solid electrolyte"'),
}


# ==================================================================
# 2. 本地标注词表  —— 这是全脚本最该被你反复迭代的部分
#    先跑一遍看 UNTAGGED 比例，>15% 就说明词表不够，继续加
# ==================================================================
RX = {
    # ---- 电解质形态 ----
    "el_sulfide":  r"\b(li6ps5|li3ps4|lgps|argyrodite|li7p3s11|"
                   r"sulfide (solid )?electrolyte|thiophosphate)\b",
    "el_oxide":    r"\b(llzo|llto|latp|lagp|garnet|nasicon|perovskite electrolyte|"
                   r"oxide solid electrolyte)\b",
    "el_halide":   r"\b(li3incl6|li3ycl6|halide (solid )?electrolyte|li3yb)\b",
    "el_polymer":  r"\b(peo|poly\(ethylene oxide\)|solid polymer electrolyte|\bspe\b|"
                   r"pvdf-hfp|polymer electrolyte)\b",
    "el_quasi":    r"\b(quasi-solid|gel polymer electrolyte|\bgpe\b|gel electrolyte|"
                   r"in-?situ polymeriz|semi-solid)\b",
    "el_liquid":   r"\b(dol/dme|1,3-dioxolane|dimethoxyethane|tegdme|"
                   r"ether electrolyte|carbonate electrolyte|liquid electrolyte|"
                   r"electrolyte solution|e/s ratio|lean electrolyte|"
                   r"localized high.concentration|sparingly solvating|"
                   r"fluorinated ether|hfe\b|\btte\b|\bbtfe\b)\b",

    # ---- 正极类型（你问的关键维度）----
    "ca_span":     r"\b(span|sulfurized polyacrylonitrile|sulfurized pan|"
                   r"sulfur.?pan|s@pan)\b",
    "ca_sc":       r"\b(sulfur/carbon|s/c composite|carbon.sulfur composite|"
                   r"sulfur host|porous carbon.*sulfur|s@c\b)\b",
    "ca_li2s":     r"\b(li2s cathode|lithium sulfide cathode|li2s/)\b",
    "ca_ss":       r"\b(sulfur.*(cathode|composite).*(sulfide|solid electrolyte))\b",

    # ---- 机理（B 层，用于假设 1）----
    "me_shuttle":  r"\b(shuttle effect|polysulfide shuttle|shuttling|"
                   r"polysulfide dissolution|lips? adsorption|polysulfide adsorption)\b",
    "me_solvation": r"\b(solvation (structure|shell)|donor number|\bdn\b|"
                    r"solvating power|coordination structure)\b",
    "me_interface": r"\b(solid.solid (contact|interface)|interfacial (contact|resistance)|"
                    r"space charge|interphase|point contact)\b",
    "me_percol":   r"\b(percolation|ionic.electronic (mixed )?conduct|"
                   r"triple phase|mixed conduct)\b",
    "me_volume":   r"\b(volume (change|expansion)|80\s*%|volumetric strain)\b",
    "me_dendrite": r"\b(dendrite|critical current density|\bccd\b|lithium plating)\b",
    "me_pressure": r"\b(stack pressure|applied pressure|\bmpa\b|external pressure)\b",
}
RX = {k: re.compile(v, re.I) for k, v in RX.items()}

SOLID_KEYS  = ("el_sulfide", "el_oxide", "el_halide", "el_polymer")
LIQUID_KEYS = ("el_liquid",)


def rebuild_abstract(inv):
    """OpenAlex 的 abstract 是倒排索引，需要重建。"""
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def tag(text):
    return {k for k, rx in RX.items() if rx.search(text)}


# ==================================================================
# 3. 三层节点体系 —— 可坍缩
# ==================================================================
def assign(tags, is_lis):
    """返回 (L1, L2, L3)，任一层可能为 None（= 无法判定）。"""
    solid  = any(t in tags for t in SOLID_KEYS)
    liquid = "el_liquid" in tags
    quasi  = "el_quasi" in tags

    if is_lis:
        if quasi and not solid:
            form = "QSS"
        elif solid and not liquid:
            form = "S"
        elif liquid and not solid:
            form = "L"
        elif solid and liquid:
            form = "S"          # 同时命中：多为固态论文对比液态，归固态，但计入 AMBIG
        else:
            return (None, None, None)

        L1 = f"{form}-LiS"

        # L2：按正极路线拆（你问的那个维度）
        if "ca_span" in tags:
            route = "SPAN"
        elif "ca_li2s" in tags:
            route = "Li2S"
        elif "ca_sc" in tags or "ca_ss" in tags:
            route = "S-C"
        else:
            route = "route?"
        L2 = f"{L1}|{route}"

        # L3：正极路线 × 电解质子类
        if   "el_sulfide" in tags: sub = "sulfide"
        elif "el_halide"  in tags: sub = "halide"
        elif "el_oxide"   in tags: sub = "oxide"
        elif "el_polymer" in tags: sub = "polymer"
        elif quasi:                sub = "gel"
        elif liquid:               sub = "ether"
        else:                      sub = "el?"
        L3 = f"{L2}|{sub}"
        return (L1, L2, L3)

    # 非锂硫 → 固态锂离子（知识提供者，不按正极细分，只按电解质分）
    if solid or quasi:
        if   "el_sulfide" in tags: sub = "sulfide"
        elif "el_halide"  in tags: sub = "halide"
        elif "el_oxide"   in tags: sub = "oxide"
        elif "el_polymer" in tags: sub = "polymer"
        else:                      sub = "gel"
        return ("S-LiB", f"S-LiB|{sub}", f"S-LiB|{sub}")
    return (None, None, None)


def fetch(name, query):
    out, cursor, page = [], "*", 0
    while cursor:
        params = {
            "filter": (f"title_and_abstract.search:{query},"
                       f"from_publication_date:{YEAR_FROM}-01-01,type:article"),
            "select": "id,title,publication_year,abstract_inverted_index,referenced_works",
            "per-page": 200, "cursor": cursor, "api_key": KEY,
        }
        if MAILTO:
            params["mailto"] = MAILTO
        r = requests.get(API, params=params, timeout=90)
        if r.status_code == 429:
            print("  [429] 限流，等 15s…"); time.sleep(15); continue
        r.raise_for_status()
        d = r.json()
        if page == 0:
            print(f"  meta.count = {d['meta']['count']:,}")
        out.extend(d["results"])
        cursor = d["meta"].get("next_cursor")
        page += 1
        print(f"  page {page:>4}  累计 {len(out):,}", end="\r")
        time.sleep(0.15)
    print()
    return out


def report_level(level_name, node_of, works_by_id):
    """输出某一层的节点规模 + 边矩阵 + GO/NO-GO。"""
    sizes = Counter(node_of.values())
    edges = defaultdict(int)
    for wid, src in node_of.items():
        for ref in works_by_id[wid].get("referenced_works") or []:
            tgt = node_of.get(ref)
            if tgt:
                edges[(src, tgt)] += 1

    nodes = [n for n, c in sizes.most_common() if c >= 20]
    print(f"\n{'='*72}\n{level_name}  （只显示 >=20 篇的节点）\n{'='*72}")
    for n in nodes:
        print(f"  {n:<28} {sizes[n]:>7,} 篇")

    print(f"\n  引文边矩阵（行=接收/施引, 列=提供/被引）")
    w = max(len(n) for n in nodes) + 2 if nodes else 10
    print(" " * w + "".join(f"{n[:13]:>15}" for n in nodes))
    for a in nodes:
        print(f"{a:<{w}}" + "".join(f"{edges[(a,b)]:>15,}" for b in nodes))

    print(f"\n  GO/NO-GO（跨节点边，自环不计）")
    any_green = False
    for a in nodes:
        for b in nodes:
            if a == b:
                continue
            n = edges[(a, b)]
            if n == 0:
                continue
            flag = "GREEN " if n >= 300 else ("YELLOW" if n >= 100 else "RED   ")
            if n >= 300:
                any_green = True
            print(f"    {a:>26} <- {b:<26} {n:>8,}  {flag}")
    print(f"\n  → 本层{'可用' if any_green else '不足，需坍缩到更粗的层级'}")
    return edges


def main():
    raw = {}
    for name, q in WIDE_QUERIES.items():
        print(f"\n[宽检索 {name}] 拉取中…")
        for w in fetch(name, q):
            raw[w["id"]] = w
    print(f"\n去重后共 {len(raw):,} 篇")

    node_l1, node_l2, node_l3 = {}, {}, {}
    tagstat, untagged, ambig = Counter(), 0, 0

    for wid, w in raw.items():
        text = (w.get("title") or "") + " " + rebuild_abstract(
            w.get("abstract_inverted_index"))
        t = tag(text)
        tagstat.update(t)
        is_lis = bool(re.search(
            r"lithium.?sulf|li-?s batter|span|sulfurized polyacrylonitrile|li2s",
            text, re.I))
        if is_lis and any(k in t for k in SOLID_KEYS) and "el_liquid" in t:
            ambig += 1
        a, b, c = assign(t, is_lis)
        if a is None:
            untagged += 1
            continue
        node_l1[wid], node_l2[wid], node_l3[wid] = a, b, c

    print(f"\n标注结果：已归类 {len(node_l1):,} / 未归类 {untagged:,} "
          f"({untagged/max(len(raw),1):.1%}) / 液固同时命中 {ambig:,}")
    if untagged / max(len(raw), 1) > 0.15:
        print("  ⚠️  未归类比例 >15%，词表 RX 需要继续补充后重跑")

    print("\n各标签命中量（用于校准词表）：")
    for k, v in tagstat.most_common():
        print(f"    {k:<16} {v:>7,}")

    e1 = report_level("L1  粗颗粒（推荐作为网络节点）", node_l1, raw)
    e2 = report_level("L2  中颗粒（正极路线拆分）",     node_l2, raw)
    e3 = report_level("L3  细颗粒（正极 × 电解质）",    node_l3, raw)

    with open("preflight_v2_result.json", "w", encoding="utf-8") as f:
        json.dump({
            "n_works": len(raw), "untagged": untagged, "ambiguous": ambig,
            "tag_counts": dict(tagstat),
            "L1": {f"{a}->{b}": v for (a, b), v in e1.items()},
            "L2": {f"{a}->{b}": v for (a, b), v in e2.items()},
            "L3": {f"{a}->{b}": v for (a, b), v in e3.items()},
        }, f, ensure_ascii=False, indent=2)
    print("\n已写出 preflight_v2_result.json")
    print("\n决策规则：选「最细的、跨节点边仍 >=300 的那一层」作为网络节点，"
          "更细的维度全部降级为属性标签。")


if __name__ == "__main__":
    main()
