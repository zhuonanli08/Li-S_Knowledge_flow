import json
import re
from pathlib import Path

root = Path(r"D:\Desktop\课题一锂硫知识流动分析\output\方案D_试点")
source_dir = root / "候选问题筛选" / "全文文本"
data = json.loads((root / "全库文献索引_中间数据.json").read_text(encoding="utf-8"))
records = {r["编号"]: r for r in data["solid_lis_records"]}
page_re = re.compile(r"===\s*第\s*(\d+)\s*页\s*===")
metric_re = re.compile(r"\d+(?:\.\d+)?\s*(?:wt\s*%|%|mAh|mA\s*h|mg\s*cm|mg/cm|MPa|kPa|°C|℃|\s*C\b|S\s*cm|mS\s*cm|cycles?|hours?|h\b)", re.I)
condition_re = re.compile(r"pressure|loading|areal capacity|stack|cut[- ]?off|voltage|wt\s*%|weight ratio|mass ratio|conductive agent|solid electrolyte|binder|carbon|catalyst|mediator|interfac|contact|tortuosity|decompos|degrad|LiI|LiVS|Li2S2|gradient|particle size|porosity", re.I)

def clean(s):
    return re.sub(r"\s+", " ", s).strip()

def split_pages(text):
    matches = list(page_re.finditer(text))
    if not matches:
        return [("?", text)]
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((m.group(1), text[m.end():end]))
    return out

def main():
    output = ["# 本地全文条件段落候选摘录", "", "> 自动按工况/组成/界面词定位；以下段落需人工确认其含义和单位，不能把关键词命中直接当作结论。", ""]
    for path in sorted(source_dir.glob("*.txt")):
        paper_id = path.stem
        meta = records.get(paper_id, {})
        output.extend([f"## {paper_id}｜{meta.get('年份','')}｜{meta.get('标题','标题未匹配')}", ""])
        pages = split_pages(path.read_text(encoding="utf-8", errors="replace"))
        scored = []
        for page, raw in pages:
            # Paragraph boundaries survive PDF extraction better than sentences.
            for para in re.split(r"\n\s*\n+", raw):
                p = clean(para)
                if len(p) < 50:
                    continue
                if re.search(r"\b(references|acknowledg(?:e)?ments|author contributions)\b", p[:160], re.I):
                    continue
                metric = bool(metric_re.search(p))
                cond = bool(condition_re.search(p))
                if not (metric and cond):
                    continue
                score = 2 * len(metric_re.findall(p)) + len(condition_re.findall(p))
                if page == "1":
                    score += 1
                scored.append((score, int(page) if page.isdigit() else 999, p))
        chosen = []
        seen = set()
        for score, page, p in sorted(scored, key=lambda x: (-x[0], x[1])):
            key = re.sub(r"\W+", "", p.lower())[:180]
            if key in seen:
                continue
            seen.add(key)
            chosen.append((page, p[:760]))
            if len(chosen) == 7:
                break
        if not chosen:
            output.append("- 未定位到带定量条件的段落；需人工查全文。")
        for page, p in sorted(chosen, key=lambda x: x[0]):
            output.append(f"- p.{page}: {p}")
        output.append("")
    target = root / "候选问题筛选" / "全文条件段落候选摘录.md"
    joined = "\n".join(output)
    target.write_text(joined, encoding="utf-8")
    print(f"wrote {target}; papers={len(list(source_dir.glob('*.txt')))}; chars={len(joined)}")

if __name__ == "__main__":
    main()
