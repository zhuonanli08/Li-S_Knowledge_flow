"""抽查用：打印未归类样本、各"类别×范围"命中样本（命中短语前后截取），供人工判 ✅🔶❌。"""
import json, random, re, sys
from common import OUT

sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open(OUT / '_inventory.json', encoding='utf-8'))
mode = sys.argv[1] if len(sys.argv) > 1 else 'hits'
rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 20261019)


def snip(s, ph, w=110):
    i = s.find(ph)
    if i < 0: return s[:2 * w]
    return ('…' if i > w else '') + s[max(0, i - w):i] + '【' + ph + '】' + s[i + len(ph):i + len(ph) + w] + '…'


if mode == 'uncl':
    scope = sys.argv[3]
    us = [u for u in d['unclassified'] if u['范围'] == scope and not u['只命中负极专用']]
    for u in rnd.sample(us, min(int(sys.argv[4]) if len(sys.argv) > 4 else 15, len(us))):
        print(f"[{u['编号']}] {u['标题'][:150]}\n    做法句: {u['做法句'][:330]}")
elif mode == 'hits':
    codes = sys.argv[3].split(',')
    k = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    for code in codes:
        for scope in ['液态锂硫', '固态锂金属', '固态锂硫', '固态锂硫_全部年份']:
            rs = [r for r in d['rows'] if r['类别编号'] == code and r['范围'] == scope]
            if not rs: continue
            print(f"\n## {code} {rs[0]['方法类别'][:20]} | {scope} n={len(rs)}")
            for r in rnd.sample(rs, min(k, len(rs))):
                print(f"  [{r['编号']}|{r['证据来源']}|{r['作用位置（按命中句）']}] {snip(r['原句（规范化）'], r['命中短语'])}")
elif mode == 'na':
    for r in rnd.sample(d['na_rows'], int(sys.argv[3]) if len(sys.argv) > 3 else 15):
        print(f"[{r['范围']}|{r['类别编号']}|{r['作用位置（按命中句）']}] {snip(r['原句（规范化）'], r['命中短语'])}")
