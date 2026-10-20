"""打印某类方法在固态锂硫（全部）的原句和来源体系代表句，供人工判读。用法：print_class.py M01,M02 [每类最多条数]"""
import json, sys, random
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
r = json.load(open(Path(__file__).resolve().parent / '_step3a_evidence.json', encoding='utf-8'))
codes = sys.argv[1].split(',')
k = int(sys.argv[2]) if len(sys.argv) > 2 else 60
rnd = random.Random(1)


def snip(s, ph, w=150):
    i = s.find(ph)
    if i < 0: return s[:2 * w]
    return s[max(0, i - w):i + len(ph) + w]


for c in codes:
    e = r[c]
    allr = e['固态锂硫']['全部原句']
    show = allr if len(allr) <= k else sorted(rnd.sample(allr, k), key=lambda x: x['年份'])
    print(f"\n######## {c} {e['类别']} — 固态锂硫 {len(allr)} 条（显示 {len(show)}）")
    for x in show:
        print(f"  [{x['年份']}|{x['电解质']}|{x['DOI']}] {snip(x['原句'], x['命中'])}")
    for src in ('液态锂硫', '固态锂金属'):
        for x in e[src]['代表原句']:
            print(f"  〔{src}·{x['年份']}|{x['组分']}|{x['DOI']}〕 {snip(x['原句'], x['命中'], 120)}")
