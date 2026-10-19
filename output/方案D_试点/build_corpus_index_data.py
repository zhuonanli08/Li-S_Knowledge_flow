import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(r"D:\Desktop\课题一锂硫知识流动分析")
DATA = ROOT / "output" / "dataset_v2" / "论文表.csv"
CITATIONS = ROOT / "output" / "dataset_v2" / "引用表.csv"

# Broad, overlapping title/abstract retrieval labels. These identify papers for
# review; a hit is not treated as full-text confirmation of a mechanism.
LABELS = {
    "正极材料与硫转化": re.compile(r"cathode|sulfur host|sulfur cathode|composite cathode|cathode architecture|cathode design|lithium sulfide|li2s|sulfur conversion|sulfur redox|sulfurized", re.I),
    "碳宿主与电子网络": re.compile(r"carbon|graphene|graphite|carbon nanotube|\bcnt\b|carbon fiber|carbon black|porous carbon|conductive additive|electronic conductivity", re.I),
    "电解质组成与反应": re.compile(r"electrolyte|sulfide|thiophosphate|argyrodite|li6ps5|halide electrolyte|polymer electrolyte|decomposition|electrochemical stability|electrochemical window", re.I),
    "界面与接触": re.compile(r"interface|interfacial|contact|interlayer|coating|coated|surface modification|reaction layer|space-charge|wetting", re.I),
    "催化与介体": re.compile(r"catalyst|catalytic|mediator|redox shuttle|redox-active|electrocatal|iodide|iodine|reaction kinetics|conversion kinetics", re.I),
    "载量压力与实用条件": re.compile(r"high[- ]sulfur[- ]loading|sulfur loading|areal capacity|areal loading|stack pressure|low pressure|thick electrode|lean electrolyte", re.I),
    "加工与空间结构": re.compile(r"ball mill|milling|sinter|processing|fabrication|three-dimensional|\b3d\b|gradient|in situ|mechanochemical|cold press|hot press", re.I),
}

TRANSFER_LABELS = {
    "界面与接触": re.compile(r"interface|interfacial|contact|interlayer|coating|coated|surface modification|reaction layer|space-charge|wetting", re.I),
    "电解质与稳定性": re.compile(r"electrolyte|solid electrolyte|interphase|stability|decomposition|electrochemical window|ionic conductivity|ion transport", re.I),
    "压力与机械完整性": re.compile(r"pressure|mechanical|contact|stacking|stack pressure|stress|strain|crack|fracture|void", re.I),
    "催化与氧化还原": re.compile(r"catalyst|catalytic|mediator|redox shuttle|redox-active|electrocatal|iodide|iodine|redox kinetics", re.I),
    "碳与导电网络": re.compile(r"carbon|graphene|graphite|carbon nanotube|\bcnt\b|carbon fiber|conductive network|electronic conductivity", re.I),
    "加工与结构": re.compile(r"processing|fabrication|in situ|sinter|milling|gradient|three-dimensional|\b3d\b|composite", re.I),
}

def norm_text(row):
    return f"{row.get('标题','')} {row.get('摘要','')}"

def label_row(row, rules):
    text = norm_text(row)
    return [name for name, pattern in rules.items() if pattern.search(text)]

def main(out_path):
    with DATA.open("r", encoding="utf-8-sig", newline="") as f:
        papers = list(csv.DictReader(f))
    with CITATIONS.open("r", encoding="utf-8-sig", newline="") as f:
        citation_rows = list(csv.DictReader(f))

    # Unique target citing papers per referenced item, split by source group.
    target_citers = defaultdict(set)
    target_citing_groups = defaultdict(set)
    cited_by_group = Counter()
    for c in citation_rows:
        if c.get("引用方分组") != "固态锂硫":
            continue
        cited_id = c.get("被引方编号", "")
        cited_group = c.get("被引方分组", "")
        if cited_id:
            target_citers[cited_id].add(c.get("引用方编号", ""))
            target_citing_groups[(cited_group, cited_id)].add(c.get("引用方编号", ""))
        cited_by_group[cited_group] += 1

    groups = defaultdict(list)
    for row in papers:
        groups[row.get("分组", "")].append(row)

    solid = groups["固态锂硫"]
    liquid = groups["液态锂硫"]
    quasi = groups["准固态锂硫"]
    solid_battery = groups["固态锂电池"]

    solid_rows = []
    solid_label_counts = Counter()
    solid_year_counts = Counter()
    solid_type_counts = Counter()
    for r in solid:
        labels = label_row(r, LABELS)
        solid_label_counts.update(labels)
        solid_year_counts.update([r.get("年份", "") or "未标年"])
        solid_type_counts.update([r.get("文献类型", "未标类型") or "未标类型"])
        solid_rows.append({
            "编号": r.get("编号", ""), "年份": r.get("年份", ""), "文献类型": r.get("文献类型", ""),
            "标题": r.get("标题", ""), "DOI": r.get("DOI", ""), "主题标签": "；".join(labels),
            "摘要": r.get("摘要", ""), "摘要可用": r.get("有摘要", ""), "电解质类型": r.get("电解质类型", ""),
            "正极路线": r.get("正极路线", ""), "本地PDF登记路径": r.get("本地PDF", ""),
            "被固态锂硫库引用的篇数": len(target_citers.get(r.get("编号", ""), set())),
            "来源": r.get("来源", ""),
        })

    # Liquid Li-S strategy pool: include all non-empty abstracts with at least
    # one strategy label. The complete database remains summarized on Overview.
    transfer_rows = []
    transfer_counts = Counter()
    pool_counts = Counter()
    liquid_hits = 0
    for r in liquid:
        if not r.get("摘要", "").strip():
            continue
        labels = label_row(r, TRANSFER_LABELS)
        if not labels:
            continue
        liquid_hits += 1
        transfer_counts.update(("液态锂硫", x) for x in labels)
        transfer_rows.append({
            "体系": "液态锂硫", "编号": r.get("编号", ""), "年份": r.get("年份", ""),
            "文献类型": r.get("文献类型", ""), "标题": r.get("标题", ""), "DOI": r.get("DOI", ""),
            "策略主题": "；".join(labels), "摘要": r.get("摘要", ""),
            "被固态锂硫库引用的篇数": len(target_citing_groups.get(("液态锂硫", r.get("编号", "")), set())),
            "来源": r.get("来源", ""),
        })
    pool_counts["液态锂硫记录"] = len(liquid)
    pool_counts["液态锂硫有摘要"] = sum(bool(r.get("摘要", "").strip()) for r in liquid)
    pool_counts["液态锂硫策略主题命中"] = liquid_hits

    # Solid-state lithium-metal source pool, separated from the much broader
    # all-solid-state battery group using an explicit title/abstract filter.
    lithium_metal_re = re.compile(r"lithium[- ]metal|li[- ]metal|metal anode|lithium anode|anode[- ]free|lithium plating|lithium stripping", re.I)
    ssb_hits = 0
    for r in solid_battery:
        if not r.get("摘要", "").strip():
            continue
        text = norm_text(r)
        if not lithium_metal_re.search(text):
            continue
        ssb_hits += 1
        labels = label_row(r, TRANSFER_LABELS)
        transfer_counts.update(("固态锂金属/负极相关固态电池", x) for x in labels)
        transfer_rows.append({
            "体系": "固态锂金属/负极相关固态电池", "编号": r.get("编号", ""), "年份": r.get("年份", ""),
            "文献类型": r.get("文献类型", ""), "标题": r.get("标题", ""), "DOI": r.get("DOI", ""),
            "策略主题": "；".join(labels), "摘要": r.get("摘要", ""),
            "被固态锂硫库引用的篇数": len(target_citing_groups.get(("固态锂电池", r.get("编号", "")), set())),
            "来源": r.get("来源", ""),
        })
    pool_counts["固态锂电池记录"] = len(solid_battery)
    pool_counts["固态锂电池有摘要"] = sum(bool(r.get("摘要", "").strip()) for r in solid_battery)
    pool_counts["锂金属/负极词命中且有摘要"] = ssb_hits

    # Quasi-solid Li-S is retained as a boundary comparison rather than folded
    # into the all-solid target group.
    for r in quasi:
        if not r.get("摘要", "").strip():
            continue
        labels = label_row(r, TRANSFER_LABELS)
        if not labels:
            continue
        transfer_counts.update(("准固态锂硫（边界对照）", x) for x in labels)
        transfer_rows.append({
            "体系": "准固态锂硫（边界对照）", "编号": r.get("编号", ""), "年份": r.get("年份", ""),
            "文献类型": r.get("文献类型", ""), "标题": r.get("标题", ""), "DOI": r.get("DOI", ""),
            "策略主题": "；".join(labels), "摘要": r.get("摘要", ""),
            "被固态锂硫库引用的篇数": len(target_citing_groups.get(("准固态锂硫", r.get("编号", "")), set())),
            "来源": r.get("来源", ""),
        })
    pool_counts["准固态锂硫记录"] = len(quasi)
    pool_counts["准固态锂硫有摘要"] = sum(bool(r.get("摘要", "").strip()) for r in quasi)

    # Rank source-system items first by actual citation bridges from solid Li-S,
    # then by year. This prioritizes connection, not paper quality.
    transfer_rows.sort(key=lambda x: (int(x["被固态锂硫库引用的篇数"] or 0), int(x["年份"] or 0)), reverse=True)

    bridges = Counter()
    for c in citation_rows:
        if c.get("引用方分组") == "固态锂硫":
            bridges[c.get("被引方分组", "")] += 1
    top_bridges = []
    for src_group, cnt in bridges.most_common():
        if src_group in ("液态锂硫", "固态锂电池", "准固态锂硫"):
            top_bridges.append({"来源体系": src_group, "固态锂硫引用记录数": cnt})

    def group_counts(rows):
        return {
            "记录数": len(rows),
            "摘要数": sum(bool(r.get("摘要", "").strip()) for r in rows),
            "年份最早": min((int(r["年份"]) for r in rows if str(r.get("年份", "")).isdigit()), default=None),
            "年份最新": max((int(r["年份"]) for r in rows if str(r.get("年份", "")).isdigit()), default=None),
        }

    summary = {
        "source_path": str(DATA), "target_group": "固态锂硫", "target": group_counts(solid),
        "target_types": dict(solid_type_counts), "target_years": dict(sorted(solid_year_counts.items())),
        "target_label_counts": dict(solid_label_counts), "source_pools": {
            "液态锂硫": group_counts(liquid), "液态锂硫策略主题命中": liquid_hits,
            "固态锂电池": group_counts(solid_battery), "锂金属/负极词命中且有摘要": ssb_hits,
            "准固态锂硫": group_counts(quasi),
        },
        "source_topic_counts": {f"{g}｜{label}": n for (g, label), n in transfer_counts.items()},
        "target_citation_bridges": top_bridges,
        "definitions": {
            "固态锂硫标签": "题名+摘要多标签检索；关键词命中用于建立复核队列，不代表人工确认机制或效果。",
            "来源体系范围": "液态锂硫为有摘要且命中至少一个策略标签的记录；固态锂电池先用题名/摘要的锂金属/负极词筛选；准固态锂硫独立保留作边界对照。",
            "引用桥接": "引用表中引用方分组为固态锂硫的记录计数；显示目标库是否引用来源体系文献，不等于方案有效性或引用质量。",
        },
    }
    out = {"summary": summary, "solid_lis_records": solid_rows, "transfer_records": transfer_rows}
    Path(out_path).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"summary": summary, "solid_rows": len(solid_rows), "transfer_rows": len(transfer_rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python build_corpus_index_data.py <output.json>")
    main(sys.argv[1])
