"""分析一敏感性检验：按 敏感性情景清单.csv 改固态锂硫组的分组标签，其余参数与冻结版一致，重跑分析一，结果另存。

用法：python sensitivity_analysis1.py <dataset_v2 目录> <analysis1_v2.py> <敏感性情景清单.csv> <输出目录>
情景：基线（不改，用来核对能否逐字复现冻结结果）、A 已确认错误修正、B 严格全固态边界。
改法：只改标签、不删引用关系。被改的论文在论文表里换组；在引用表里作为引用方时换组（于是移出固态锂硫引用方），
作为被引方时改记新组；新组为"不进组"的，从论文表删除，引用它的记"池外"（与冻结版 D7 的做法一致）。
不覆盖冻结目录里的任何文件。
"""
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

SCEN = {'基线': None, '情景A': '情景 A（已确认错误修正）', '情景B': '情景 B（严格全固态边界）'}
DUMP = '''
import json as _json
_json.dump({"n_citing": len(sl), "S2": S2, "SK": SK, "SA": SA, "S1": S1}, open("情景摘要.json", "w", encoding="utf-8"), ensure_ascii=False, default=str)
'''


def relabel(pp, ct, changes):
    pp, ct = pp.copy(), ct.copy()
    drop = [p for p, g in changes.items() if g == '不进组']
    keep = {p: g for p, g in changes.items() if g != '不进组'}
    for p, g in keep.items():
        pp.loc[pp['编号'] == p, '分组'] = g
        if g == '液态锂硫':
            pp.loc[pp['编号'] == p, '电解质类型'] = '不适用（液态）'
        if g == '固态锂电池':
            pp.loc[pp['编号'] == p, '正极路线'] = '不适用'
    ct['引用方分组'] = ct['引用方编号'].map(keep).fillna(ct['引用方分组'])
    ct['被引方分组'] = ct['被引方编号'].map(keep).fillna(ct['被引方分组'])
    pp = pp[~pp['编号'].isin(drop)]
    ct = ct[~ct['引用方编号'].isin(drop)].copy()
    ct.loc[ct['被引方编号'].isin(drop), '被引方分组'] = '池外'
    return pp, ct


def main(ds_dir, script, sc_csv, out_dir):
    ds, out = Path(ds_dir), Path(out_dir)
    pp0 = pd.read_csv(ds / '论文表.csv', dtype=str, keep_default_na=False)
    ct0 = pd.read_csv(ds / '引用表.csv', dtype=str, keep_default_na=False)
    sc = pd.read_csv(sc_csv, dtype=str).fillna('')
    src = Path(script).read_text(encoding='utf-8')
    res, audit = {}, []
    for name, col in SCEN.items():
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        changes = {} if col is None else {r['论文号']: r[col] for _, r in sc.iterrows() if r[col]}
        pp, ct = relabel(pp0, ct0, changes)
        if col is None:  # 基线：原样复制（不经 pandas 改写，保证逐字一致）
            (d / '论文表.csv').write_bytes((ds / '论文表.csv').read_bytes())
            (d / '引用表.csv').write_bytes((ds / '引用表.csv').read_bytes())
        else:
            pp.to_csv(d / '论文表.csv', index=False, encoding='utf-8-sig')
            ct.to_csv(d / '引用表.csv', index=False, encoding='utf-8-sig')
        cited = ct0[ct0['被引方编号'].isin(changes) & (ct0['引用方分组'] == '固态锂硫')]
        citing = pp0[pp0['编号'].isin(changes) & (pp0['来源'] == '检索') & (pp0['分组'] == '固态锂硫')]
        audit.append({'情景': name, '改动论文': len(changes), '其中移出引用方（检索来的）': len(citing),
                      '受影响的被引记录（固态锂硫引用它们的条数）': len(cited),
                      '新组分布': '；'.join(f'{k} {v}' for k, v in pd.Series(changes).value_counts().items()) if changes else '—'})
        patched = src.replace(r'os.chdir(r"D:\Desktop\课题一锂硫知识流动分析\output\dataset_v2")', f'os.chdir(r"{d.resolve()}")') + DUMP
        assert patched != src + DUMP, '没找到 chdir 语句，脚本可能已改'
        (d / '_analysis1_patched.py').write_text(patched, encoding='utf-8')
        subprocess.run([sys.executable, str(d / '_analysis1_patched.py')], check=True)
        res[name] = json.load(open(d / '情景摘要.json', encoding='utf-8'))

    same = (out / '基线' / '分析一_结果.md').read_text(encoding='utf-8') == (ds / '分析一_结果.md').read_text(encoding='utf-8')

    # 对比：二、液态 − 固态锂电池（百分点）
    rows = []
    for i, base in enumerate(res['基线']['S2']):
        r = {'子组': base[0]}
        for name in SCEN:
            s = res[name]['S2'][i]
            assert s[0] == base[0]
            r[f'{name} 篇数'] = s[1]
            r[f'{name} 差值 [95% CI]'] = f'{s[2]} [{s[3]}, {s[4]}]'
            r[f'{name} 结论'] = s[5]
        r['结论是否变化'] = '不变' if len({r[f'{n} 结论'] for n in SCEN}) == 1 else '变化'
        rows.append(r)
    cmp2 = pd.DataFrame(rows)
    # 对比：四、主表中"固态锂硫（全部）"各类占比
    head = ['子组', '篇数', '池内引用', '液态·讲电解液', '液态·正极/催化等', '固锂电池·讲电解质', '固锂电池·电极/界面等', '自己', '准固态', '池外占比']
    sa = []
    for name in SCEN:
        for row in res[name]['SA']:
            if row[0] in ('固态锂硫（全部）', '└ 2023–', '└ 电解质=硫化物', '└ 电解质=聚合物'):
                sa.append([name] + row[:len(head)])
    cmpA = pd.DataFrame(sa, columns=['情景'] + head)
    au = pd.DataFrame(audit)
    with pd.ExcelWriter(out / '敏感性检验_结果.xlsx', engine='openpyxl') as w:
        pd.DataFrame({'说明': [
            '分析一敏感性检验（2026-10-18）。基线 = 冻结数据原样重跑；情景 A = 已确认错误修正；情景 B = 严格全固态边界。清单见 组别核查_复核表.xlsx 的"敏感性情景清单"页。',
            '只改分组标签，不删引用关系；其余参数（规则、bootstrap 种子、子组划分）与冻结版一致。冻结目录未改动。',
            f'基线重跑与冻结版 分析一_结果.md 逐字一致：{"是" if same else "否"}',
            '情景清单只覆盖随机样本和定向排查标记到的论文，不是全量重判；结果稳定只能说"对目前确认的误分不敏感"。',
        ]}).to_excel(w, sheet_name='说明', index=False)
        au.to_excel(w, sheet_name='改动概况', index=False)
        cmp2.to_excel(w, sheet_name='液态−固态锂电池差值', index=False)
        cmpA.to_excel(w, sheet_name='主表占比', index=False)
    print('基线逐字复现冻结版：', same)
    print(au.to_string(index=False))
    print(cmp2[['子组'] + [c for c in cmp2.columns if '差值' in c or '篇数' in c] + ['结论是否变化']].to_string(index=False))


if __name__ == '__main__':
    main(*sys.argv[1:5])
