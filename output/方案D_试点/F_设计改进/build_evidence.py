"""Read local sources, preserve page locations, and verify the evidence excerpts."""
from pathlib import Path
import csv
import json
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OLD = OUT.parent / "F_定向核查" / "全文文本"
META = {r["编号"]: r for r in csv.DictReader((ROOT / "output/dataset_v2/论文表.csv").open(encoding="utf-8-sig"))}

# Excerpts are located in the source, never generated from an abstract paraphrase.
SPECS = [
    ("E01", "W7124424515", 3, "which indicates that more free surface area or voids still exist", "残余可接触面积", "作者解释；BET不是固固界面真实接触面积"),
    ("E02", "W7124424515", 5, "contributes 8.9%, 20.9%, and 41.5%", "容量来源", "作者用含硫/无硫电极估算；百分比增加不独立证明分解绝对量增加"),
    ("E03", "W7124424515", 10, "while effectively suppressing excessive carbon|SEs contacts", "最近已有设计", "双界面结构已有人做；不能把减少裸露碳直接当新设计"),
    ("E04", "W7167073746", 2, "When the additive of AXT reaches up to 5%", "用量非单调", "此处数值属于对称电池，不是普通含硫全电池容量"),
    ("E05", "W7167073746", 4, "low AXT coverage promotes Li2S generation", "覆盖度与产物选择", "作者基于计算和表征提出的解释；不能写为任意添加剂的普遍规律"),
    ("E06", "W7169438107", 4, "Co-M presents uniformly distributed medium-sized Co clusters", "最近已有催化设计", "约0.54 nm是该材料结果；尺寸、负载和配位并非完全独立"),
    ("E07", "W7169438107", 6, "although the Co-M/S and Co-L/S cathodes deliver lower initial capacities", "首圈容量不是唯一指标", "作者报告的同篇循环比较，不用于不同论文之间直接排名"),
    ("E08", "W7127084998", 5, "conventional preparation by direct ball-milling of all three components", "加工和位置", "Co/CNT与制备顺序同时变化；不能把性能全部归因于单一因素"),
    ("E09", "W4311764535", 2, "under a pressure of approximately 50 MPa", "运行压力", "不是制片压力；该文Li2S路线与单质硫路线分开"),
    ("E10", "W4311764535", 2, "with a weight ratio of 6:4", "配方与加工", "Li2S:VGCF先5:1，再复合物:LPS为6:4；推算最终50:10:40，不当单质硫配方"),
    ("E11", "W7128180073", 2, "not all iodine-containing SEs exhibit distinct redox-mediating behavior", "含碘不等于起介体作用", "作者总结，须继续核对具体相组成"),
    ("E12", "W7128180073", 6, "likely insufficient to quantify and separate", "无硫扣除的限制", "高倍率电流分布和动力学不同；扣除只能在条件支持时作估算"),
    ("E13", "W4406385644", 6, "only occurs unidirectionally on charge", "介体作用有方向性", "本文LBPSI条件下充电介导；不泛化为所有含碘材料"),
    ("E14", "W7124464532", 10, "abandons preloaded elemental sulfur", "无预加硫路线边界", "主动用电解质产生活性物质，不与常规含硫正极按每克硫容量排名"),
    ("E15", "F5", 2, "an electronically conductive polymer coating may not prevent degradation completely", "非硫固态来源", "电子隔离功能；不同电位及导电需求限制直接移植"),
    ("E16", "F5", 1, "A thin alumina coating with a few nanometers thickness", "非硫固态已有实现", "ALD包覆VGCF；并非已证明适用于所有硫正极"),
    ("E17", "W4404035015", 2, "CoI2 has satisfactory solubility in ether electrolytes", "液态来源成立条件", "溶解与多硫化物反应是液态前提；不是固态配方推荐"),
    ("E18", "W4404035015", 2, "when charged to 3.1 V", "液态介体激活代价", "不能直接把液态3.1 V充电激活搬到硫化物固态电池"),
]

def norm(s):
    return re.sub(r"[\s\-‐‑‒–—−\u00ad]", "", unicodedata.normalize("NFKC", s)).lower()

def pages(path):
    parts = re.split(r"=== 第 (\d+) 页 ===", path.read_text(encoding="utf-8"))
    return {int(parts[i]): re.sub(r"\s+", " ", parts[i + 1]).strip() for i in range(1, len(parts), 2)}

records = []
for eid, pid, page, anchor, use, limit in SPECS:
    path = (OUT / "来源文本/W4404035015.txt") if pid == "W4404035015" else ((OUT.parent / "全文文本/F5.txt") if pid == "F5" else OLD / f"{pid}.txt")
    t = pages(path)[page]
    idx = t.lower().find(anchor.lower())
    assert idx >= 0, (eid, pid, page, anchor)
    start = max(t.rfind(". ", 0, idx), t.rfind("? ", 0, idx))
    start = start + 2 if start >= 0 else max(0, idx - 100)
    end = t.find(". ", idx + len(anchor))
    end = min(len(t), idx + len(anchor) + 250) if end < 0 else end + 1
    quote = t[start:end]
    assert norm(quote) in norm(t)
    meta = META.get(pid, {})
    records.append(dict(id=eid, paper=pid, page=page, quote=quote, use=use, limitation=limit, source=str(path), doi=meta.get("DOI", "10.1021/acs.chemmater.0c04454" if pid == "F5" else ""), title=meta.get("标题", "On the Additive Microstructure in Composite Cathodes and Alumina-Coated Carbon Microwires for Improved All-Solid-State Batteries")))

si = OUT / "来源文本/W7167073746_SI_段落.txt"
si_text = si.read_text(encoding="utf-8")
for eid, para, anchor, use, limit in [
    ("E19", 14, "with mass ratio of 3:7", "AXT工作基础配方", "KB:S=3:7，KB/S:LPSC=4:6，推算未加AXT时S:C:LPSC=28:12:60；0.5–10 wt%的分母未明确写出，不能擅自补定"),
    ("E20", 15, "The additional pressure of 50 MPa", "AXT工作运行压力", "冷压200 MPa、负极压制100 MPa与循环50 MPa须分开；力学监测装置另记"),
    ("E21", 16, "under 30 ℃", "AXT工作电位温度", "正文与SI的Li-In标注和窗口对应关系不宜自行精确换算；主方案先选Li参比明确的配置"),
]:
    p = next(line for line in si_text.splitlines() if line.startswith(f"[段落 {para}]"))
    assert anchor in p
    records.append(dict(id=eid, paper="W7167073746", page=f"SI段落{para}", quote=p.split("] ",1)[1], use=use, limitation=limit, source=str(si), doi=META["W7167073746"]["DOI"], title=META["W7167073746"]["标题"]))

lines = ["# F 设计改进：证据与定位", "", "> 日期：2026-10-19。18条正文摘录 + 3条SI段落记录。页码是本地PDF顺序页；SI为DOCX文本段落号，不冒充页码。所有摘录均核对本地文本存在；这不等于机制已证实。", "", "含硫固态正文重点查阅8篇相关段落：W7124424515、W7167073746、W7169438107、W7127084998、W4311764535、W7128180073、W4406385644、W7124464532；加查AXT的SI；来源体系核读非硫固态F5相关段落及液态W4404035015相关段落。不称为逐篇通读正文与全部SI。", ""]
for r in records:
    lines.extend([f"## {r['id']}｜{r['use']}", "", f"- 文献：{r['paper']}；{r['title']}；DOI：{r['doi']}", f"- 定位：{r['page']}；[本地文本]({r['source'].replace(chr(92), '/')})", f"- 支持边界：{r['limitation']}", "", "> " + r["quote"], ""])
(OUT / "F_证据与定位.md").write_text("\n".join(lines), encoding="utf-8")
(OUT / "证据核验.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

# This is a reproducible bounded lead search, NOT a novelty clearance.
all_rows = list(META.values())
solid = [r for r in all_rows if r["分组"] == "固态锂硫" and r.get("来源") != "补池"]
# Match the original candidate scope using explicit search provenance.
from collections import Counter
source_counts = dict(Counter(r.get("来源", "") for r in all_rows if r["分组"] == "固态锂硫"))
patterns = {
    "覆盖或用量×界面": (r"astaxanthin|coverage|surface.coverage|dosage|dose", r"interface|electrolyte|carbon"),
    "碘介体×接触结构": (r"iod|LiI|redox.mediat", r"contact|interface|carbon|microstruct|phase"),
    "催化×电解质分解": (r"cataly", r"electrolyte.{0,60}(?:decompos|degrad)|(?:decompos|degrad).{0,60}electrolyte"),
}
search = {}
pool = [r for r in all_rows if r["分组"] == "固态锂硫"]
for name, pats in patterns.items():
    hits = [r for r in pool if all(re.search(p, r["标题"] + " " + r["摘要"], re.I) for p in pats)]
    search[name] = [{k:r[k] for k in ["编号", "年份", "标题", "DOI", "来源"]} for r in hits]
full_hits = {}
for name, pats in patterns.items():
    hits=[]
    for path in sorted(OLD.glob("*.txt")):
        text=re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
        # Exclude references only when an explicit section heading exists.
        text=re.split(r"\bREFERENCES\b|\bReferences\b",text)[0]
        if all(re.search(p,text,re.I) for p in pats):hits.append(path.stem)
    full_hits[name]=hits
report = ["# F 定向线索检索记录", "", "日期：2026-10-19。只用于找最接近已有工作，不是创新性检索结论。", "", f"初始固态锂硫分组记录：{len(pool)}篇；其中非空摘要{sum(bool(r['摘要'].strip()) for r in pool)}篇；来源字段分布：{source_counts}。该搜索包含补池，不与原初筛1146/887分母混用。分组误差沿用原库局限。", f"全文关键词联检范围：已有F页码文本{len(list(OLD.glob('*.txt')))}份；正文关键段落实质复核范围另见证据表。不把联检命中称为读过全文。", "", "联检指同一文档两组词同时出现，不证明已研究它们的交互；零命中也不证明无人做过。", ""]
for name,pats in patterns.items():
    report.extend([f"## {name}", "", f"正则：`{pats[0]}` AND `{pats[1]}`", f"标题摘要命中{len(search[name])}篇；已有F全文文本联检命中{len(full_hits[name])}篇。", "", "| 编号 | 年份 | 题目 | 来源字段 |", "|---|---|---|---|"])
    report.extend(f"| {r['编号']} | {r['年份']} | {r['标题'].replace('|','/')} | {r['来源']} |" for r in search[name])
    report.extend(["", "全文联检编号：" + "、".join(full_hits[name]), ""])
(OUT/"F_定向检索记录.md").write_text("\n".join(report),encoding="utf-8")
(OUT/"定向检索.json").write_text(json.dumps(dict(abstract=search,fulltext=full_hits),ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"excerpts_verified":len(records),"abstract_pool":len(pool),"nonempty_abstracts":sum(bool(r['摘要'].strip()) for r in pool),"local_texts_searched":len(list(OLD.glob('*.txt'))),"hits":{k:len(v) for k,v in search.items()}},ensure_ascii=False))
