# -*- coding: utf-8 -*-
"""分析一（读数据集 v2）：固态锂硫的参考文献来自哪里
算法与 v1 相同；引用方只取检索来的固态锂硫（补池论文只作被引方）
  一、v1 → v2 对比；二、液态 vs 固态锂电池 的差值；三、表 A = 被引方含综述；四、表 B = 被引方去掉综述（引综述视作引池外）；五、池中数量
括号 = 95% 置信区间（按引用方论文有放回重抽 1000 次）
输出 output/dataset_v2/分析一_结果.md 和 分析一_结果.xlsx（内容相同）
数据集 v1 已删除（2026-10-11）；对比用的 v1 数字在删除前从 dataset_v1 算出，固定在下面 V1_POINTS
"""
import os
import numpy as np, pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
os.chdir(r"D:\Desktop\课题一锂硫知识流动分析\output\dataset_v2")
pp = pd.read_csv("论文表.csv", dtype=str)
ct0 = pd.read_csv("引用表.csv", dtype=str)

# v1 的点估计：液态·讲电解液, 液态·正极/催化等, 固锂电池·讲电解质, 固锂电池·电极/界面等, 自己, 准固态, 液态合计, 固锂电池合计, 池外占比
V1_POINTS = {
    "固态锂硫（全部）": (1363, [6.62, 33.85, 25.64, 7.02, 26.25, 0.63, 40.47, 32.65, 41.43]),
    "└ 电解质=硫化物": (253, [4.56, 22.23, 31.92, 11.19, 29.84, 0.25, 26.80, 43.11, 35.22]),
    "└ 电解质=聚合物": (409, [7.99, 40.78, 24.98, 3.04, 22.38, 0.83, 48.77, 28.02, 40.55]),
    "└ 路线=单质硫复合": (517, [7.04, 40.88, 18.69, 5.69, 27.05, 0.66, 47.92, 24.38, 34.89]),
    "└ 路线=SPAN": (52, [8.68, 27.32, 35.02, 5.87, 22.00, 1.10, 36.00, 40.89, 40.44]),
    "└ 2013–2018": (267, [10.66, 52.43, 14.44, 4.59, 17.49, 0.39, 63.09, 19.03, 51.24]),
    "└ 2019–2022": (433, [6.80, 34.94, 26.23, 6.53, 24.79, 0.71, 41.74, 32.76, 42.81]),
    "└ 2023–": (663, [5.69, 29.48, 27.54, 7.79, 28.87, 0.63, 35.17, 35.33, 38.05]),
}
V1_N_CITING, V1_INPOOL = 1363, 48053

SRC = ["液态锂硫·讲电解液", "液态锂硫·正极/催化等", "固态锂电池·讲电解质", "固态锂电池·电极/界面等", "固态锂硫自己", "准固态锂硫"]
def cat(g, e):
    if g == "液态锂硫": return "液态锂硫·讲电解液" if e == "是" else "液态锂硫·正极/催化等"
    if g == "固态锂电池": return "固态锂电池·讲电解质" if e == "是" else "固态锂电池·电极/界面等"
    return {"固态锂硫": "固态锂硫自己", "准固态锂硫": "准固态锂硫", "池外": "池外"}[g]
sl = pp[(pp["分组"] == "固态锂硫") & (pp["来源"] == "检索")].set_index("编号")
n_keep = int((sl["v1 分组"] == "固态锂硫").sum())
n_add, n_rm = len(sl) - n_keep, V1_N_CITING - n_keep

def matrix(ct, idx):
    ct = ct[ct["引用方分组"] == "固态锂硫"]
    c = pd.Series([cat(g, e) for g, e in zip(ct["被引方分组"], ct["被引方标题讲电解质"])], index=ct.index)
    M = ct.assign(来源类=c).groupby(["引用方编号", "来源类"]).size().unstack(fill_value=0)
    return M.reindex(columns=SRC + ["池外"], fill_value=0).reindex(idx, fill_value=0)
ctB = ct0.copy()
rv = (ctB["被引方文献类型"] == "review") & (ctB["被引方分组"] != "池外")
ctB.loc[rv, "被引方分组"] = "池外"
MA, MB = matrix(ct0, sl.index), matrix(ctB, sl.index)

y = sl["年份"].astype(int)
rows = [("固态锂硫（全部）", sl.index)]
for k in ["硫化物", "聚合物", "氧化物", "凝胶/准固态", "复合", "硼氢化物", "卤化物/氯化物", "未标明"]:
    rows.append((f"└ 电解质={k}", sl.index[sl["电解质类型"] == k]))
for k in ["单质硫复合", "SPAN", "Li2S 正极", "有机硫", "未标明"]:
    rows.append((f"└ 路线={k}", sl.index[sl["正极路线"] == k]))
for a, b, lab in [(0, 2018, "2013–2018"), (2019, 2022, "2019–2022"), (2023, 9999, "2023–")]:
    rows.append((f"└ {lab}", sl.index[(y >= a) & (y <= b)]))
rd = dict(rows)

def boot(ids, M, f, seed=20261010):
    rng = np.random.default_rng(seed); X = M.loc[ids].to_numpy(float); n = len(X)
    return np.array([f(X[rng.integers(0, n, n)].sum(0)) for _ in range(1000)])
def table_row(name, ids, M):
    X = M.loc[ids, SRC].to_numpy(float); out = M.loc[ids, "池外"].to_numpy(float)
    n = len(ids); tot = X.sum()
    if n < 15 or tot == 0: return [name, n, "论文太少，不报"] + [""] * (len(SRC) + 1)
    share = X.sum(0) / tot * 100
    lo, hi = np.percentile(boot(ids, M[SRC], lambda s: s / s.sum() * 100), [2.5, 97.5], axis=0)
    return [name, n, int(tot)] + [f"{v:.1f} [{a:.1f}, {b:.1f}]" for v, a, b in zip(share, lo, hi)] + [f"{out.sum() / (out.sum() + tot) * 100:.0f}%"]
def point(ids, M):
    X = M.loc[ids, SRC].to_numpy(float).sum(0); out = M.loc[ids, "池外"].to_numpy(float).sum()
    s = X / X.sum() * 100
    return list(s) + [s[0] + s[1], s[2] + s[3], out / (out + X.sum()) * 100]
gap = lambda s: (s[0] + s[1] - s[2] - s[3]) / s[:6].sum() * 100   # 液态合计 − 固态锂电池合计（百分点）

# ---------- 各节内容（md 和 xlsx 共用） ----------
CMP = list(V1_POINTS)
c_sl = ct0[ct0["引用方分组"] == "固态锂硫"]
inpool = c_sl[c_sl["被引方分组"] != "池外"]
NOTES = ["本文件取代已删除的 dataset_v1/分析一_结果.md（v1 的数字见第一节对比）",
         "v2 相对 v1：① 把固态锂硫引用了、但检索没捞到的文献（2010 年前、综述、检索式没覆盖的写法）按同一套规则补进池，只作被引方；"
         "② 分组规则补漏：硫化物全固态和无摘要的固态电池标题默认算锂体系，固态锂电池补认 superionic conductor，锂硫补认标题里的老写法",
         f"引用方：固态锂硫 {len(sl):,} 篇（v1 为 {V1_N_CITING:,} 篇；规则补漏新进 {n_add} 篇、移出 {n_rm} 篇）",
         f"固态锂硫的参考文献共 {len(c_sl):,} 条：落在池内 {len(inpool):,} 条（v1 为 {V1_INPOOL:,} 条），"
         f"其中指向补池论文 {int((inpool['被引方来源'] == '补池').sum()):,} 条、指向综述 {int((inpool['被引方文献类型'] == 'review').sum()):,} 条",
         "每行把一批固态锂硫论文的参考文献摊开，看落在哪一类；六类加起来 = 100%（只算落在池内的引用），最后一列 = 落在池外的比例",
         "方括号 = 95% 置信区间；两组区间不重叠，才能说有差别；论文少于 15 篇的子组不报",
         "主结果被引方含综述（用户 2026-10-11 定）；去掉综述的版本见第六页，作稳健性检验"]
S1_HEAD = ["子组", "版本", "篇数", "液态·讲电解液", "液态·正极/催化等", "固锂电池·讲电解质", "固锂电池·电极/界面等", "自己", "准固态", "液态合计", "固态锂电池合计", "池外占比"]
S1 = []
for k in CMP:
    n1, v1 = V1_POINTS[k]
    S1.append([k.replace("└ ", ""), "v1", n1] + [round(x, 1) for x in v1])
    for ver, M in [("v2", MA)]:   # 主结果含综述（2026-10-11 用户定）；去掉综述的版本放最后一页作稳健性检验
        S1.append([k.replace("└ ", ""), ver, len(rd[k])] + [round(x, 1) for x in point(rd[k], M)])
S2_HEAD = ["子组", "篇数", "液态 − 固态锂电池（百分点；负数 = 引固态锂电池更多）", "95% CI 下限", "95% CI 上限", "结论"]
S2 = []
for k in CMP:
    ids = rd[k]; v = gap(MA.loc[ids, SRC].to_numpy(float).sum(0)); lo, hi = np.percentile(boot(ids, MA[SRC], gap), [2.5, 97.5])
    S2.append([k.replace("└ ", ""), len(ids), round(v, 1), round(lo, 1), round(hi, 1),
               "引液态更多" if lo > 0 else ("引固态锂电池更多" if hi < 0 else "差别不显著")])
# KF / RKF（方案 §5.1，对标 Nature Energy）：KF = 引某类的次数 ÷ 全部参考文献（含池外）× 100；RKF = KF(某类) ÷ KF(自引) × 100
# 液态锂硫按方案口径给两版：讲电解液（主）、全部液态（对照）；固态锂电池同理
def kf_f(s):
    tot, self_ = s.sum(), s[4]
    cnt = [s[0], s[0] + s[1], s[2], s[2] + s[3]]
    return np.array([c / tot * 100 for c in cnt] + [self_ / tot * 100] + [c / self_ * 100 for c in cnt])
K_HEAD = ["子组", "篇数", "全部参考文献", "KF 液态·讲电解液", "KF 液态（全部）", "KF 固态锂电池·讲电解质", "KF 固态锂电池（全部）", "KF 自引",
          "RKF 液态·讲电解液", "RKF 液态（全部）", "RKF 固态锂电池·讲电解质", "RKF 固态锂电池（全部）"]
SK = []
for k in CMP:
    ids = rd[k]; M_ = MA[SRC + ["池外"]]
    v = kf_f(M_.loc[ids].to_numpy(float).sum(0)); lo, hi = np.percentile(boot(ids, M_, kf_f), [2.5, 97.5], axis=0)
    SK.append([k.replace("└ ", ""), len(ids), int(M_.loc[ids].to_numpy().sum())] + [round(x, 1) for x in v[:5]] +
              [f"{v[i]:.0f} [{lo[i]:.0f}, {hi[i]:.0f}]" for i in range(5, 9)])
T_HEAD = ["固态锂硫子组", "篇数", "池内引用"] + SRC + ["池外占比"]
SA = [table_row(n, ids, MA) for n, ids in rows]
SB = [table_row(n, ids, MB) for n, ids in rows]
pc = pp.assign(类=[cat(g, e) for g, e in zip(pp["分组"], pp["标题讲电解质"])])
S5_HEAD = ["类", "检索来的", "补池·article", "补池·review", "补池·其他类型"]
S5 = []
for k in SRC:
    s = pc[pc["类"] == k]; b = s[s["来源"] == "补池"]
    S5.append([k, int((s["来源"] == "检索").sum()), int((b["文献类型"] == "article").sum()), int((b["文献类型"] == "review").sum()),
               int((~b["文献类型"].isin(["article", "review"])).sum())])
SECTIONS = [("一、v1 → v2 对比（点估计，%）", "每行是一批固态锂硫论文，各列是它们的参考文献里某一类占多少；前六列加起来 = 100%。液态合计 = 液态两类相加，固态锂电池合计同理", S1_HEAD, S1),
            ("二、液态锂硫合计 − 固态锂电池合计（百分点）", "正数 = 引液态锂硫更多，负数 = 引固态锂电池更多；95% 区间跨过 0（一正一负）= 两边没有显著差别", S2_HEAD, S2),
            ("三、KF 与 RKF（方案 §5.1，对标 Nature Energy）", "KF = 引某类的次数 ÷ 全部参考文献（含池外）× 100；RKF = KF(某类) ÷ KF(自引) × 100，"
             "即「引某类的量相当于引自己的百分之几」，方括号为 95% 置信区间。液态按方案口径给讲电解液（主）和全部液态（对照）两版。"
             "对标：Nature Energy 那篇锂电石墨 → 钠电硬碳 RKF = 67.7。注意固态锂硫领域小、自引基数低，RKF 会偏高", K_HEAD, SK),
            ("四、主表：各类占比和 95% 置信区间", "每格 = 占比 [下限, 上限]（%），分母是池内引用；两组区间不重叠，才能说有差别", T_HEAD, SA),
            ("五、各类被引论文在池中的数量", "论文多的类自然被引得多，比较时要记住这一点。补池论文只是被固态锂硫或准固态锂硫引用过的那部分，不是该领域的全部论文，不能拿来算存量基准线", S5_HEAD, S5),
            ("六、稳健性检验：被引方去掉综述", "把引综述视作引池外，其余与主表相同。和主表对比，各项差别不超过约 0.4 个百分点，结论不变", T_HEAD, SB)]

# ---------- md ----------
fmt = lambda v: f"{v:,}" if isinstance(v, int) else (f"{v:.1f}" if isinstance(v, float) else str(v))
L = ["# 分析一：固态锂硫的参考文献来自哪里（数据集 v2，2026-10-11）\n"] + [f"- {x}" for x in NOTES]
for title, note, head, body in SECTIONS:
    L += [f"\n## {title}\n"] + ([note + "\n"] if note else []) + ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    L += ["| " + " | ".join(fmt(v) for v in r) + " |" for r in body]
open("分析一_结果.md", "w", encoding="utf-8").write("\n".join(L))

# ---------- xlsx ----------
FONT = Font(name="Arial", size=10); BOLD = Font(name="Arial", size=10, bold=True)
HFILL = PatternFill("solid", start_color="D9D9D9"); WRAP = Alignment(wrap_text=True, vertical="top")
wb = Workbook(); ws = wb.active; ws.title = "说明"
ws.append(["分析一：固态锂硫的参考文献来自哪里（数据集 v2，2026-10-11）"]); ws["A1"].font = BOLD
for x in NOTES: ws.append([x])
ws.column_dimensions["A"].width = 150
for title, note, head, body in SECTIONS:
    w = wb.create_sheet(title.split("、")[0] + "、" + title.split("、")[1][:24].replace("：", " ").replace("/", "·"))
    w.append([title]); w["A1"].font = BOLD
    if note: w.append([note])
    w.append(head); hr = w.max_row
    for c in w[hr]: c.font = BOLD; c.fill = HFILL; c.alignment = WRAP
    for r in body: w.append(r)
    for i in range(len(head)): w.column_dimensions[chr(65 + i)].width = 24 if i == 0 else 15
    w.freeze_panes = w.cell(row=hr + 1, column=2)
for w in wb.worksheets:
    for row in w.iter_rows():
        for c in row:
            if c.font != BOLD: c.font = FONT
wb.save("分析一_结果.xlsx")
print("\n".join(L[:12])); print("\n".join("| " + " | ".join(fmt(v) for v in r) + " |" for r in S2))
