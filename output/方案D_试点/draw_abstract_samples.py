"""方案D §9.1 词表试点：从三组可用摘要中分层抽样，一次抽出三批（互不重叠）。

批1 = 第一版词表（开放式抽取），批2 = 修订词表，批3 = 独立验证集（词表稳定前不打开）。
分层 = 时段 × 材料类别；每组每批 20 篇，按层大小的平方根分配（兼顾覆盖小层和比例）。
批1 每组至少有 1 篇标题像综述的，没抽到就换入 1 篇（抽样方式记"有意加入：综述"）。

用法：python draw_abstract_samples.py <论文表.csv> <输出.csv>
"""
import sys
import numpy as np
import pandas as pd

SEED = 20261018
N_PER_GROUP = 20
MIN_ABSTRACT_CHARS = 300  # 短于此的多为被截断的摘要（如 RSC 只给一两句）
GROUPS = {'固态锂电池': '非硫固态', '固态锂硫': '固态锂硫', '液态锂硫': '液态锂硫'}
REVIEW_RE = r'\breview\b|progress|perspective|challenges|overview|roadmap|outlook'


def allocate(sizes, n):
    """按 sqrt(层大小) 分配 n 个名额，最大余数法取整，不超过层大小。"""
    w = np.sqrt(sizes.astype(float))
    raw = w / w.sum() * n
    k = np.minimum(np.floor(raw).astype(int), sizes)
    rem = raw - np.floor(raw)
    while k.sum() < n:
        cand = [i for i in np.argsort(-rem) if k[i] < sizes[i]]
        k[cand[0]] += 1
        rem[cand[0]] = -1
    return k


def main(src, out):
    rng = np.random.default_rng(SEED)
    d = pd.read_csv(src, dtype=str).fillna('')
    d = d[(d['来源'] == '检索') & d['分组'].isin(GROUPS)]
    d = d[d['摘要'].str.len() >= MIN_ABSTRACT_CHARS].copy()
    d['年'] = pd.to_numeric(d['年份'])
    d['时段'] = pd.cut(d['年'], [0, 2017, 2021, 2100], labels=['2010-2017', '2018-2021', '2022-']).astype(str)
    d['材料类别'] = np.where(d['分组'] == '液态锂硫', d['正极路线'], d['电解质类型'])
    d['材料类别'] = d['材料类别'].replace('', '未标明')
    d['像综述'] = d['标题'].str.contains(REVIEW_RE, case=False, regex=True)

    rows, used = [], set()
    for batch in (1, 2, 3):
        for g, name in GROUPS.items():
            pool = d[(d['分组'] == g) & ~d['编号'].isin(used)]
            strata = pool.groupby(['时段', '材料类别']).size()
            k = allocate(strata.values, N_PER_GROUP)
            picked = []
            for (seg, mat), m in zip(strata.index, k):
                if m == 0:
                    continue
                s = pool[(pool['时段'] == seg) & (pool['材料类别'] == mat)]
                picked += list(rng.choice(s['编号'].values, size=m, replace=False))
            how = {p: '分层随机' for p in picked}
            if batch == 1 and not pool[pool['编号'].isin(picked)]['像综述'].any():
                rv = pool[pool['像综述'] & ~pool['编号'].isin(picked)]
                if len(rv):
                    big = pool[pool['编号'].isin(picked)].groupby(['时段', '材料类别'])['编号'].apply(list)
                    drop = big.loc[big.map(len).idxmax()][-1]
                    picked.remove(drop)
                    add = rng.choice(rv['编号'].values)
                    picked.append(add)
                    how[add] = '有意加入：综述'
            used.update(picked)
            for p in picked:
                r = pool[pool['编号'] == p].iloc[0]
                rows.append({'批次': batch, '组': name, '论文号': p, 'DOI': r['DOI'], '年份': r['年份'],
                             '时段': r['时段'], '材料类别': r['材料类别'], '抽样方式': how.get(p, '分层随机'),
                             '标题': r['标题'], '摘要字数': len(r['摘要'])})
    o = pd.DataFrame(rows).sort_values(['批次', '组', '时段', '材料类别'])
    o.to_csv(out, index=False, encoding='utf-8-sig')
    print(f'可用摘要池（≥{MIN_ABSTRACT_CHARS} 字符）：', d.groupby('分组').size().rename(GROUPS).to_dict())
    print('每批每组篇数：', o.groupby(['批次', '组']).size().unstack().to_dict('index'))
    b1 = o[o['批次'] == 1]
    print('\n批1 时段分布：'); print(pd.crosstab(b1['组'], b1['时段']).to_string())
    print('\n批1 材料类别分布：'); print(pd.crosstab(b1['材料类别'], b1['组']).to_string())
    print('\n批1 抽样方式：'); print(b1['抽样方式'].value_counts().to_string())


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
