"""方案D 组别核查：从冻结 v2 的固态锂硫组简单随机抽 60 篇（口径见 试点计划.md §D1）。

抽样框 = 论文表.csv 中 分组 = 固态锂硫 的全部论文（检索 + 补池），按编号去重。
不因缺摘要、难判断或与批1 重合而换样。另附每篇的判据材料：v2 摘要、库摘要、本地全文路径。

用法：python draw_group_check_sample.py <论文表.csv> <library.json> <摘要样本_三批.csv> <输出.csv>
"""
import json
import sys

import numpy as np
import pandas as pd

SEED = 20261018
N = 60


def main(src, lib_json, batch_csv, out):
    d = pd.read_csv(src, dtype=str).fillna('')
    frame = d[d['分组'] == '固态锂硫'].drop_duplicates('编号')
    rng = np.random.default_rng(SEED)
    picked = rng.choice(frame['编号'].values, size=N, replace=False)
    s = frame.set_index('编号').loc[picked].reset_index()

    lib = json.load(open(lib_json, encoding='utf-8'))['papers']
    lib = {k.lower(): v for k, v in lib.items()}
    b1 = pd.read_csv(batch_csv, dtype=str)
    b1 = set(b1.loc[b1['批次'] == '1', '论文号'])

    rows = []
    for i, r in s.iterrows():
        e = lib.get(r['DOI'].lower(), {}) if r['DOI'] else {}
        rows.append({
            '序号': i + 1, '论文号': r['编号'], 'DOI': r['DOI'], '年份': r['年份'], '标题': r['标题'],
            '来源': r['来源'], 'v2 电解质类型': r['电解质类型'], 'v2 正极路线': r['正极路线'],
            'v2 判定依据': r['判定依据'][:300], '文献类型(OpenAlex)': r['文献类型'],
            'v2 摘要字数': len(r['摘要']), '库摘要字数': len(e.get('abstract') or ''),
            '库主题': e.get('topic', ''), '本地全文': e.get('pdf_file', ''), '本地SI': e.get('si_file', ''),
            '与批1重合': '是' if r['编号'] in b1 else '否',
        })
    o = pd.DataFrame(rows)
    o.to_csv(out, index=False, encoding='utf-8-sig')
    print(f'抽样框 {len(frame)} 篇（来源：{frame["来源"].value_counts().to_dict()}），抽 {N} 篇，种子 {SEED}')
    print('样本来源：', o['来源'].value_counts().to_dict())
    print('v2 有摘要：', (o['v2 摘要字数'] > 0).sum(), '｜仅库摘要：', ((o['v2 摘要字数'] == 0) & (o['库摘要字数'] > 0)).sum(),
          '｜两者都无但有本地全文：', ((o['v2 摘要字数'] == 0) & (o['库摘要字数'] == 0) & (o['本地全文'] != '')).sum(),
          '｜只有标题：', ((o['v2 摘要字数'] == 0) & (o['库摘要字数'] == 0) & (o['本地全文'] == '')).sum())
    print('有本地全文：', (o['本地全文'] != '').sum(), '｜与批1重合：', (o['与批1重合'] == '是').sum())
    print('v2 电解质类型：', o['v2 电解质类型'].value_counts().to_dict())


if __name__ == '__main__':
    main(*sys.argv[1:5])
