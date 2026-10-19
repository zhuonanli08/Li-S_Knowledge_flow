"""最终抽查样本（固定种子）：每个"类别×组"2 条（三组），不适用 12 条，未归类 12 条。输出 _final_audit_sample.json 供人工判定。"""
import json, random, sys
from common import OUT

sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open(OUT / '_inventory.json', encoding='utf-8'))
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20261019  # 第 1 轮 20261019（用于修规则），验收轮 20261020
rnd = random.Random(SEED)
sample = []
codes = sorted({r['类别编号'] for r in d['rows']})
for code in codes:
    for scope in ['液态锂硫', '固态锂金属', '固态锂硫']:
        rs = [r for r in d['rows'] if r['类别编号'] == code and r['范围'] == scope]
        for r in rnd.sample(rs, min(2, len(rs))):
            sample.append(dict(r, 抽查组='适用'))
for r in rnd.sample(d['na_rows'], 12):
    sample.append(dict(r, 抽查组='不适用行'))
uncl = [u for u in d['unclassified'] if u['范围'] != '固态锂硫_全部年份']
for u in rnd.sample(uncl, 12):
    sample.append(dict(u, 抽查组='未归类'))
json.dump(sample, open(OUT / '_final_audit_sample.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
for i, r in enumerate(sample):
    if r['抽查组'] == '未归类':
        print(f"{i:>3} 未归类 {r['范围'][:5]} [{r['编号']}] {r['标题'][:110]} || {r['做法句'][:160]}")
    else:
        s, ph = r['原句（规范化）'], r['命中短语']
        j = s.find(ph)
        snip = s[max(0, j - 90):j] + '【' + ph + '】' + s[j + len(ph):j + len(ph) + 90]
        print(f"{i:>3} {r['抽查组'][:3]} {r['类别编号']} {r['范围'][:5]} {r['作用位置（按命中句）']} | {snip}")
