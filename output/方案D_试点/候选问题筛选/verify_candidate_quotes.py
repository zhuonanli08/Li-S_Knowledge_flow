"""核对 证据原句_待核.csv 里的原句：全文句在 全文文本/<论文号>.txt 里逐字查找并报页码，
摘要句、标题句在冻结论文表里查找（忽略空白、连字符、连字和大小写差异）。
检索记录、内部记录不是原句，记"不适用"。补上年份、题名后写出 证据原句.csv。

用法：python verify_candidate_quotes.py <候选问题筛选目录> <dataset_v2 目录>
"""
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd


def norm(s):
    return re.sub(r'[\s\-‐‑‒–—―−­]', '', unicodedata.normalize('NFKC', s)).lower()


def load(path):
    buf, spans, pos, cur = [], [], 0, None
    for part in re.split(r'(=== 第 \d+ 页 ===)', path.read_text(encoding='utf-8')):
        m = re.fullmatch(r'=== 第 (\d+) 页 ===', part)
        if m:
            cur = int(m.group(1))
            continue
        s = norm(part)
        buf.append(s)
        spans.append((pos, pos + len(s), cur))
        pos += len(s)
    return ''.join(buf), spans


def main(d, ds):
    d, ds = Path(d), Path(ds)
    ev = pd.read_csv(d / '证据原句_待核.csv', dtype=str).fillna('')
    pp = pd.read_csv(ds / '论文表.csv', dtype=str, low_memory=False).fillna('').set_index('编号')
    texts = {p.stem: load(p) for p in (d / '全文文本').glob('*.txt')}
    res, pages, years, titles = [], [], [], []
    for _, r in ev.iterrows():
        w, src, q = r['论文号'], r['来源'], r['原句']
        years.append(pp.at[w, '年份'] if w in pp.index else '')
        titles.append(pp.at[w, '标题'] if w in pp.index else '')
        if src in ('检索记录', '内部记录'):
            res.append('不适用'); pages.append(''); continue
        if src == '全文':
            s, spans = texts[w]
            i = s.find(norm(q))
            res.append('✅ 找到' if i >= 0 else '❌ 未找到')
            pages.append(next((str(p) for a, b, p in spans if a <= i < b), '') if i >= 0 else '')
        else:
            field = '摘要' if src == '摘要' else '标题'
            ok = w in pp.index and norm(q) in norm(pp.at[w, field])
            res.append('✅ 找到' if ok else '❌ 未找到'); pages.append(field)
    ev.insert(3, '年份', years)
    ev.insert(4, '题名', titles)
    ev['核对'] = res
    ev['位置'] = pages
    ev.to_csv(d / '证据原句.csv', index=False, encoding='utf-8-sig')
    for _, r in ev.iterrows():
        print(f"{r['核对']}｜{r['证据号']} {r['论文号']} {r['位置']}｜{r['原句'][:60]}")
    n = (ev['核对'] != '不适用').sum()
    print(f"\n原句 {n} 条：找到 {(ev['核对'] == '✅ 找到').sum()}，未找到 {(ev['核对'] == '❌ 未找到').sum()}；检索/内部记录 {len(ev) - n} 条")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
