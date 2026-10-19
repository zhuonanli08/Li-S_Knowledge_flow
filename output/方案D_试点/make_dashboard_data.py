"""把本轮结果整理成看板用的 CSV（每个数都来自本轮实际输出文件）。

用法：python make_dashboard_data.py <方案D_试点目录> <dataset_v2 目录> <输出目录>
"""
import json
import sys
from pathlib import Path

import pandas as pd


def main(pilot, ds, out):
    pilot, ds, out = Path(pilot), Path(ds), Path(out)
    out.mkdir(parents=True, exist_ok=True)

    # 1 分析一敏感性检验：液态 − 固态锂电池 差值及 95% CI
    rows = []
    for name, lab in [('基线', '冻结版'), ('情景A', '情景 A'), ('情景B', '情景 B')]:
        js = json.load(open(pilot / '敏感性检验' / name / '情景摘要.json', encoding='utf-8'))
        for r in js['S2']:
            rows.append({'子组': r[0], '情景': lab, '篇数': r[1], '差值': r[2], '下限': r[3], '上限': r[4], '结论': r[5]})
    sens = pd.DataFrame(rows)
    chg = sens.groupby('子组')['结论'].nunique()
    sens['结论是否变化'] = sens['子组'].map(lambda k: '变化' if chg[k] > 1 else '不变')
    sens.to_csv(out / 'sens.csv', index=False, encoding='utf-8')

    # 2 一致性检查：被移出（情景 A）与保留的检索论文，其池内参考文献落在哪一组
    pp = pd.read_csv(ds / '论文表.csv', dtype=str, low_memory=False).fillna('')
    ct = pd.read_csv(ds / '引用表.csv', dtype=str).fillna('')
    sc = pd.read_csv(pilot / '敏感性情景清单.csv', dtype=str).fillna('')
    A = set(sc.loc[sc['情景 A（已确认错误修正）'] != '', '论文号'])
    sl = pp[(pp['分组'] == '固态锂硫') & (pp['来源'] == '检索')]
    mix = []
    for lab, ids in [('情景 A 移出的论文', set(sl[sl['编号'].isin(A)]['编号'])), ('保留的论文', set(sl[~sl['编号'].isin(A)]['编号'])),
                     ('移出的聚合物子组', set(sl[sl['编号'].isin(A) & (sl['电解质类型'] == '聚合物')]['编号'])),
                     ('保留的聚合物子组', set(sl[~sl['编号'].isin(A) & (sl['电解质类型'] == '聚合物')]['编号']))]:
        c = ct[ct['引用方编号'].isin(ids) & (ct['被引方分组'] != '池外')]
        vc = c['被引方分组'].value_counts()
        for g in ['液态锂硫', '固态锂电池', '固态锂硫', '准固态锂硫']:
            mix.append({'论文组': lab, '引用方篇数': len(ids), '被引方分组': g, '条数': int(vc.get(g, 0)), '占比': round(vc.get(g, 0) / len(c), 4)})
    pd.DataFrame(mix).to_csv(out / 'refmix.csv', index=False, encoding='utf-8')

    # 3 组别核查 60 篇：v2 语义归组分类计数
    g = pd.read_excel(pilot / '组别核查_复核表.xlsx', sheet_name='组别核查_60篇').fillna('')
    cats = ['符合', '不符合（已确认）', '不符合（判断性）', '边界未明确', '证据不足']
    pd.DataFrame([{'类别': c, '篇数': int((g['v2 语义归组'] == c).sum()),
                   '序号': '、'.join('#' + str(x) for x in g[g['v2 语义归组'] == c]['序号']) if c != '符合' else ''} for c in cats]
                 ).to_csv(out / 'group60.csv', index=False, encoding='utf-8')

    # 4 敏感性情景清单：两个情景下的改组去向
    sc2 = pd.read_excel(pilot / '组别核查_复核表.xlsx', sheet_name='敏感性情景清单').fillna('')
    srows = []
    for lab, col in [('情景 A', '情景 A（已确认错误修正）'), ('情景 B', '情景 B（严格全固态边界）')]:
        for k, v in sc2[sc2[col] != ''][col].value_counts().items():
            srows.append({'情景': lab, '改为': k, '篇数': int(v)})
    pd.DataFrame(srows).to_csv(out / 'scen.csv', index=False, encoding='utf-8')

    # 5 定位缺口：补前 / 补后
    gap = pd.read_excel(pilot / '全文表样_5篇_v0.2.xlsx', sheet_name='定位缺口').fillna('')
    pd.DataFrame([{'阶段': '补之前（10-18）', '全部缺口': 86, '开发案例涉及': 23},
                  {'阶段': '补之后（10-19）', '全部缺口': len(gap), '开发案例涉及': int((gap['属开发案例'] == '是').sum())}]
                 ).to_csv(out / 'gaps.csv', index=False, encoding='utf-8')

    # 6 案例 D01：R1 三种硫正极（原文第 5 页）
    pd.DataFrame([
        {'正极': 'AB/S', '路线': '不包覆', '首圈容量': 1247, '300圈容量': 859, '保持率': 0.725},
        {'正极': 'LPO@AB-S', '路线': '先包碳，再载硫（直接移植）', '首圈容量': 1136, '300圈容量': 665, '保持率': 0.594},
        {'正极': 'LPO@AB/S', '路线': '载硫后整体包覆（改造）', '首圈容量': 1322, '300圈容量': 1070, '保持率': 0.864},
    ]).to_csv(out / 'r1.csv', index=False, encoding='utf-8')

    # 7 案例 D01：F5（非硫固态，NCM）第 50 圈容量保持，来自比较页
    c = pd.read_excel(pilot / '全文表样_5篇_v0.2.xlsx', sheet_name='比较').set_index('比较号')
    pd.DataFrame([
        {'正极': '无碳', '保持率': c.at['F5-C3', '对照值'] / 100, '取值方式': '读图（图 8a），约值'},
        {'正极': '未包覆 VGCF', '保持率': c.at['F5-C3', '样品值'] / 100, '取值方式': '正文'},
        {'正极': 'AlxOy 包覆 VGCF', '保持率': c.at['F5-C4', '样品值'] / 100, '取值方式': '正文'},
    ]).to_csv(out / 'f5.csv', index=False, encoding='utf-8')

    # 8 案例 D01：候选与决策（设计决策案例_D01.md §6）
    pd.DataFrame([
        {'候选': 'C0', '做法': '常规导电碳，控制碳量与截止电位', '来源': '固态锂硫 F2', '决策': '作对照基线', '理由': '目标体系已有做法'},
        {'候选': 'C1', '做法': '宽带隙含氮宿主，限制界面局部电子传输', '来源': '固态锂硫 F1', '决策': '已有设计', '理由': '可作阳性对照'},
        {'候选': 'C2a', '做法': '先给导电碳包绝缘层，再载硫（直接移植）', '来源': '非硫固态 F5', '决策': '指定条件下排除',
         '理由': 'R1 中先包碳路线首圈更低、保持更差；R2 中 VGCF 作硫载体利用率低'},
        {'候选': 'C2b', '做法': '载硫后整体包离子导电层', '来源': '固态锂硫 R1（2024）', '决策': '已有设计', '理由': '不把已发表做法包装成新方案'},
        {'候选': 'C2c', '做法': '包覆纤维碳只作长程导体，另有载硫碳', '来源': '分析者推断', '决策': '证据不足暂缓', '理由': '无直接证据；暂缓不等于排除'},
    ]).to_csv(out / 'd01.csv', index=False, encoding='utf-8')
    for p in sorted(out.glob('*.csv')):
        print(p.name, len(pd.read_csv(p)))


if __name__ == '__main__':
    main(*sys.argv[1:4])
