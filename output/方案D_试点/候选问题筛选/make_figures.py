"""画候选问题初筛的两张图：图1 当前进度、图2 候选依据矩阵。内容与 候选问题筛选表.md 一致。

用法：python make_figures.py <输出目录>
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle, Wedge

for f in ('C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/msyhbd.ttc'):
    font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Microsoft YaHei'

INK, INK2, INK3, LINE = '#18202b', '#4a5464', '#7a8494', '#d5dae2'
ACCENT, ACCENT_SOFT = '#2d4fa0', '#e3e9f7'
GOOD, GOOD_SOFT = '#1f7a4d', '#e2f2ea'
WARN, WARN_SOFT = '#9a6200', '#fbefd9'
NEU, NEU_SOFT = '#5d6675', '#eceff3'
BG = '#ffffff'


def box(ax, x, y, w, h, fc, ec, lw=1.2, r=0.06):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f'round,pad=0,rounding_size={r}',
                                fc=fc, ec=ec, lw=lw))


def mark(ax, x, y, state, s=0.11):
    """状态记号：形状和颜色同时编码，不只靠颜色。"""
    if state == 'yes':
        ax.add_patch(Circle((x, y), s, fc=GOOD, ec=GOOD))
    elif state == 'part':
        ax.add_patch(Circle((x, y), s, fc=BG, ec=WARN, lw=1.6))
        ax.add_patch(Wedge((x, y), s, 90, 270, fc=WARN, ec=WARN))
    elif state == 'unk':
        ax.add_patch(Circle((x, y), s, fc=BG, ec=INK3, lw=1.6))
    elif state == 'no':
        ax.plot([x - s, x + s], [y - s, y + s], color=INK, lw=2.2, solid_capstyle='round')
        ax.plot([x - s, x + s], [y + s, y - s], color=INK, lw=2.2, solid_capstyle='round')
    elif state == 'na':
        ax.plot([x - s, x + s], [y, y], color=INK3, lw=2, solid_capstyle='round')


# ---------------- 图1 当前进度 ----------------
STEPS = [
    ('明确主问题', 'done', '已定\n（方案D §1）'),
    ('列候选问题', 'done', '完成：5 个候选\n来自固态锂硫作者\n自己写出的取舍'),
    ('目标体系查新', 'done', '完成（本地范围）\nC 已有答案\nB 已在推进'),
    ('跨体系增量', 'part', '部分：A、F 只列出\n"待核实设想"\n还没有原文支撑'),
    ('功能与条件\n逐项对照', 'todo', '未开始\n只做 A、F'),
    ('案例任务书', 'todo', '未开始'),
    ('验证前写预测\n和否定条件', 'todo', '未开始'),
    ('补证或\n实验计划', 'todo', '未开始'),
]
GROUPS = [(0, 0, '方案D §1 主问题', NEU_SOFT, INK2),
          (1, 3, '方案D §5 候选问题筛选  ← 现在在这里', ACCENT_SOFT, ACCENT),
          (4, 6, '第二层：全文证据链', NEU_SOFT, INK2),
          (7, 7, '第三层：实验', NEU_SOFT, INK2)]


def fig_progress(out):
    W, gap = 1.9, 0.25
    fig, ax = plt.subplots(figsize=(17, 6.4), dpi=200)
    ax.set_xlim(-0.3, 8 * (W + gap) + 0.1)
    ax.set_ylim(-1.35, 4.35)
    ax.axis('off')
    ax.text(-0.2, 4.05, '图1  课题一（方案D）当前进度：候选问题初筛已完成，停在第 4 步之后',
            fontsize=17, weight='bold', color=INK, va='center')
    ax.text(-0.2, 3.62, '步骤按 10-19 定的执行顺序；上方色带对应方案D 总流程。第一层全量摘要统计暂不做，需要时再单独论证。',
            fontsize=11, color=INK2, va='center')
    for a, b, lab, fc, tc in GROUPS:
        x0 = a * (W + gap); x1 = b * (W + gap) + W
        box(ax, x0, 2.78, x1 - x0, 0.5, fc, fc, r=0.05)
        ax.text((x0 + x1) / 2, 3.03, lab, ha='center', va='center', fontsize=11.5,
                color=tc, weight='bold' if tc == ACCENT else 'normal')
    style = {'done': (GOOD_SOFT, GOOD, '已完成', 'yes'), 'part': (WARN_SOFT, WARN, '部分完成', 'part'),
             'todo': (BG, LINE, '未开始', 'unk')}
    for i, (name, st, note) in enumerate(STEPS):
        x = i * (W + gap)
        fc, ec, lab, m = style[st]
        box(ax, x, 0.0, W, 2.55, fc, ec, lw=1.6 if st != 'todo' else 1.2)
        ax.text(x + 0.16, 2.28, f'{i + 1}', fontsize=13, weight='bold', color=INK3, va='center')
        ax.text(x + W / 2, 1.83, name, ha='center', va='center', fontsize=13, weight='bold', color=INK,
                linespacing=1.15)
        mark(ax, x + 0.34, 1.22, m, s=0.1)
        ax.text(x + 0.52, 1.22, lab, fontsize=10.5, color=ec if st != 'todo' else INK3, va='center',
                weight='bold')
        ax.text(x + W / 2, 0.55, note, ha='center', va='center', fontsize=9.8, color=INK2, linespacing=1.3)
        if i < 7:
            ax.annotate('', xy=(x + W + gap - 0.02, 1.27), xytext=(x + W + 0.02, 1.27),
                        arrowprops=dict(arrowstyle='-|>', color=INK3, lw=1.2, mutation_scale=12))
    xs = 4 * (W + gap) - gap / 2
    ax.plot([xs, xs], [-0.15, 2.65], color=ACCENT, lw=2.2, ls=(0, (4, 3)))
    ax.text(xs, -0.42, '当前停点：等你审阅筛选表', ha='center', va='center', fontsize=12, color=ACCENT,
            weight='bold')
    ax.text(-0.2, -1.05, '范围：只用本地材料（固态锂硫检索论文 1,146 篇，有摘要 887 篇，本地全文 828 篇）；没有新下载，没有调用外部 API。',
            fontsize=10, color=INK3, va='center')
    fig.savefig(out, bbox_inches='tight', facecolor=BG)
    plt.close(fig)


# ---------------- 图2 候选依据矩阵 ----------------
COLS = ['真实、未决的\n设计选择', '跨体系证据\n可能改变选择', '关键前提\n有证据', '可行的\n验证方式']
ROWS = [
    ('A', '低压下保持\n正极三相接触', [
        ('yes', '6 条低压路线条件各异\n作者称"不能直接比较" [A3]'),
        ('part', '非硫固态卤氧化物正极电解质\n目标体系只在展望里提到 [A13]'),
        ('unk', '卤氧化物在硫正极电位下\n是否被还原（参照 A11）'),
        ('part', '可行，但要控压装置\n同条件比较 2–3 条路线')], ('继续核查', 'go')),
    ('F', '硫化物电解质的\n氧化还原：抑制\n还是利用', [
        ('yes', '严重分解带来衰减 [F5]\n并非所有含碘电解质有介体行为 [F8]'),
        ('part', '液态锂硫介体判据可写成预测 [F12]\n固态中介体不扩散，前提已变 [F7]'),
        ('part', '目标体系两边都有直接实验\n液态判据还没提取'),
        ('yes', '常规全固态电池\n加无硫对照电极')], ('继续核查\n建议先做', 'go')),
    ('B', '厚电极、高载量\n下的离子通路', [
        ('unk', '梯度、宿主、提高电解质比例\n有无同条件比较未逐篇核'),
        ('no', '两个母体系前提都不成立（推断）\n梯度做法目标体系已在用 [B4][B5]'),
        ('na', ''), ('na', '')], ('暂缓', 'hold')),
    ('C', '正极里用卤化物\n代替硫化物', [
        ('no', '已有答案：同配置三种卤化物\n直接比较过 [C1][C2]'),
        ('no', '"抗氧化"不是关键\n目标体系已自行得出 [C3]'),
        ('na', ''), ('na', '')], ('不作为\n新问题', 'drop')),
    ('E', '聚合物电解质：\n电导与多硫化物\n溶解', [
        ('yes', '作者明说存在两难 [E1]'),
        ('part', '增量主要来自液态锂硫溶剂化\n与课题二边界重叠'),
        ('unk', '本轮未查新到"已知—未知"\n聚合物类常含液，需逐篇核'),
        ('na', '')], ('暂缓', 'hold')),
]
SOFT = {'yes': GOOD_SOFT, 'part': WARN_SOFT, 'unk': NEU_SOFT, 'no': NEU_SOFT, 'na': BG}
LEG = [('yes', '有依据'), ('part', '部分 / 待核实'), ('unk', '未查'), ('no', '不成立 / 已有答案'), ('na', '不适用')]


def fig_matrix(out):
    x0, wr, wc, wk = 0.0, 2.45, 3.55, 1.45
    hh, hr = 0.95, 1.18
    n = len(ROWS)
    fig, ax = plt.subplots(figsize=(18.5, 9.2), dpi=200)
    tw = wr + 4 * wc + wk
    ax.set_xlim(-0.15, tw + 0.15)
    ax.set_ylim(-1.55, hh + n * hr + 1.15)
    ax.invert_yaxis()
    ax.axis('off')
    ax.text(0, -1.25, '图2  五个候选的依据矩阵：两个继续核查，三个暂缓或不作为新问题',
            fontsize=17, weight='bold', color=INK, va='center')
    ax.text(0, -0.82, '列 = 10-19 定的继续/停止依据；方括号是证据号，原句见 证据原句.csv（原句 35 条全部核对找到）。',
            fontsize=11, color=INK2, va='center')
    ax.text(0, -0.42, '"继续"只表示值得进入下一轮定向核查，不等于确认创新，也不等于批准实验。',
            fontsize=11, color=INK2, va='center')
    heads = ['候选'] + COLS + ['结论']
    xs = [x0, wr] + [wr + i * wc for i in range(1, 4)] + [wr + 4 * wc]
    ws = [wr] + [wc] * 4 + [wk]
    for x, w, h in zip(xs, ws, heads):
        ax.text(x + w / 2, hh / 2, h, ha='center', va='center', fontsize=12, weight='bold', color=INK,
                linespacing=1.2)
    ax.plot([0, tw], [hh, hh], color=INK, lw=1.4)
    for r, (key, name, cells, (concl, kind)) in enumerate(ROWS):
        y = hh + r * hr
        go = kind == 'go'
        if go:
            ax.add_patch(Rectangle((0, y), tw, hr, fc='#f6f8fd', ec='none', zorder=0))
        ax.text(0.12, y + hr / 2, key, fontsize=20, weight='bold', color=ACCENT if go else INK3, va='center')
        ax.text(0.55, y + hr / 2, name, fontsize=11.5, color=INK, va='center', linespacing=1.25,
                weight='bold' if go else 'normal')
        for c, (st, txt) in enumerate(cells):
            cx = wr + c * wc
            if st != 'na':
                box(ax, cx + 0.06, y + 0.08, wc - 0.12, hr - 0.16, SOFT[st], SOFT[st], r=0.05)
            mark(ax, cx + 0.3, y + hr / 2, st, s=0.1)
            ax.text(cx + 0.55, y + hr / 2, txt if st != 'na' else '不适用', fontsize=10.2,
                    color=INK2 if st != 'na' else INK3, va='center', linespacing=1.35)
        kx = wr + 4 * wc
        fc, ec, tc = {'go': (ACCENT, ACCENT, '#ffffff'), 'hold': (BG, WARN, WARN), 'drop': (NEU_SOFT, NEU_SOFT, NEU)}[kind]
        box(ax, kx + 0.12, y + 0.24, wk - 0.24, hr - 0.48, fc, ec, lw=1.6, r=0.08)
        ax.text(kx + wk / 2, y + hr / 2, concl, ha='center', va='center', fontsize=11.5, weight='bold',
                color=tc, linespacing=1.2)
        ax.plot([0, tw], [y + hr, y + hr], color=LINE, lw=0.9)
    ly = hh + n * hr + 0.55
    lx = 0.1
    ax.text(lx, ly, '图例：', fontsize=10.5, color=INK2, va='center')
    for i, (st, lab) in enumerate(LEG):
        mx = (0.95, 2.85, 5.0, 6.6, 9.3)[i]
        mark(ax, mx, ly, st, s=0.09)
        ax.text(mx + 0.2, ly, lab, fontsize=10.5, color=INK2, va='center')
    ax.text(tw, ly, '范围：本地材料；"本地未检出"不等于"领域内没人做过"', fontsize=10, color=INK3, va='center',
            ha='right')
    fig.savefig(out, bbox_inches='tight', facecolor=BG)
    plt.close(fig)


if __name__ == '__main__':
    d = Path(sys.argv[1])
    fig_progress(d / '图1_当前进度.png')
    fig_matrix(d / '图2_候选依据矩阵.png')
    print('ok')
