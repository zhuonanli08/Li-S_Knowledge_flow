"""F 定向核查的两张图：图3 原创论文立场随年份；图4 两条设想增量的去向与判定。
数据来自 F_汇总.json（build_f_table.py 生成），图4 的文字与 F_定向核查结论.md 一致。

用法：python make_f_figures.py <F_定向核查目录>
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import MaxNLocator

for f in ('C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/msyhbd.ttc'):
    font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Microsoft YaHei'

INK, INK2, INK3, LINE, BG = '#18202b', '#4a5464', '#7a8494', '#d5dae2', '#ffffff'
ACCENT, ACCENT_SOFT = '#2d4fa0', '#e3e9f7'
WARN, WARN_SOFT = '#9a6200', '#fbefd9'
NEU_SOFT = '#eceff3'
# 分类色按参考调色板固定顺序取前五个槽位
SERIES = [('抑制', '#2a78d6'), ('权衡', '#eb6834'), ('利用', '#1baf7a'), ('外加介体', '#eda100'), ('量化或观察', '#e87ba4')]
PERIODS = [('≤2020', lambda y: y <= 2020), ('2021–2022', lambda y: 2021 <= y <= 2022),
           ('2023–2024', lambda y: 2023 <= y <= 2024), ('2025', lambda y: y == 2025), ('2026', lambda y: y == 2026)]


def fig_stance(summ, out):
    cnt = {p: {s: 0 for s, _ in SERIES} for p, _ in PERIODS}
    for r in summ['年份立场']:
        y = int(r['年份']); s = '量化或观察' if r['立场'] in ('量化或校正', '只观察') else r['立场']
        for p, f in PERIODS:
            if f(y):
                cnt[p][s] += r['n']
    fig, ax = plt.subplots(figsize=(12, 5.6), dpi=200)
    ys = list(range(len(PERIODS)))[::-1]
    for yi, (p, _) in zip(ys, PERIODS):
        left = 0
        for s, c in SERIES:
            v = cnt[p][s]
            if v:
                ax.barh(yi, v, left=left, color=c, height=0.62, edgecolor=BG, linewidth=2)
                if v >= 2:
                    ax.text(left + v / 2, yi, str(v), ha='center', va='center', fontsize=10.5, color=BG, weight='bold')
                left += v
        ax.text(left + 0.3, yi, f'{left} 篇', va='center', fontsize=10.5, color=INK2)
    ax.set_yticks(ys, [p for p, _ in PERIODS], fontsize=11, color=INK)
    mx = max(sum(v.values()) for v in cnt.values())
    ax.set_xlim(0, mx + 3)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel('原创论文篇数', fontsize=10.5, color=INK2)
    ax.tick_params(axis='x', colors=INK3, labelsize=9.5)
    ax.grid(axis='x', color=LINE, lw=0.6); ax.set_axisbelow(True)
    for sp in ('top', 'right', 'left'):
        ax.spines[sp].set_visible(False)
    ax.spines['bottom'].set_color(LINE)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c) for _, c in SERIES], labels=[s for s, _ in SERIES],
              ncol=5, loc='lower left', bbox_to_anchor=(0, 1.0), frameon=False, fontsize=10.5)
    fig.suptitle('图3  固态锂硫原创论文怎样对待"电解质在正极里参与氧化还原"', x=0.02, ha='left', fontsize=15,
                 weight='bold', color=INK, y=1.04)
    fig.text(0.02, 0.965, f'本地 828 篇全文中逐篇读 {summ["读过"]} 篇，计入 {summ["计入"]} 篇（原创 {summ["原创"]}、综述 {summ["综述"]}）；'
             '2026 年（截至 10 月）就有 16 篇，多于 2023–2024 两年合计；立场是逐篇判断，原句见 F_逐篇复核表.xlsx。',
             fontsize=10, color=INK2)
    fig.savefig(out, bbox_inches='tight', facecolor=BG)
    plt.close(fig)


def box(ax, x, y, w, h, fc, ec, lw=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=0.08', fc=fc, ec=ec, lw=lw))


ROWS = [
    ('设想增量 1（来自液态锂硫）', '用液态介体判据\n预先预测哪种含碘电解质\n会起介体作用',
     '2021 年已把液态常用的 LiI 介体移入固态 [W3205269758]\n'
     '介体判据已写进固态综述，含"电位要合适" [W7163341456]\n'
     '已按电位排除 TiS2 作介体 [W4409200355]\n'
     '含碘相能否介导，作者归因于玻璃态或非晶富碘相 [W4406385644][W7128180073]',
     '已被目标体系吸收；\n剩下的条件是固态特有的结构，\n液态判据解释不了'),
    ('设想增量 2（来自非硫固态）', '"分解随碳比表面积增大"\n用来决定抑制方向',
     '同一工作比较三种比表面积的碳，并用无硫对照定量：\n电解质贡献 8.9% → 41.5%（第 1 → 100 圈）[W7124424515]\n'
     '"利用"一方也给出容量随碳比表面积的变化 [W7124464532]\n'
     '宿主、包覆、绝缘宿主等抑制做法已有多篇；13 篇原创用了无硫对照',
     '已被目标体系吸收'),
]


def fig_verdict(out):
    fig, ax = plt.subplots(figsize=(17, 8.6), dpi=200)
    ax.set_xlim(0, 17); ax.set_ylim(0, 8.6); ax.axis('off')
    ax.text(0.1, 8.25, '图4  候选 F 定向核查：问题仍然开放，但两条设想的跨体系增量目标体系已研究过', fontsize=16, weight='bold', color=INK)
    ax.text(0.1, 7.8, 'F = 硫化物电解质在硫正极里参与氧化还原，应该抑制还是利用。方括号是论文号，原句见 F_逐篇复核表.xlsx（78 条原句全部逐字核对找到）。',
            fontsize=10.5, color=INK2)
    heads = [(0.1, 3.0, '设想'), (3.3, 7.6, '固态锂硫里已有什么'), (11.1, 2.9, '去向')]
    for x, w, h in heads:
        ax.text(x + w / 2, 7.3, h, ha='center', fontsize=12, weight='bold', color=INK)
    for i, (tag, idea, ev, fate) in enumerate(ROWS):
        y = 5.15 - i * 2.25
        box(ax, 0.1, y, 3.0, 1.95, NEU_SOFT, NEU_SOFT)
        ax.text(0.25, y + 1.65, tag, fontsize=10.5, weight='bold', color=INK2)
        ax.text(1.6, y + 0.8, idea, ha='center', va='center', fontsize=11, color=INK, linespacing=1.35)
        box(ax, 3.3, y, 7.6, 1.95, BG, LINE)
        ax.text(3.45, y + 0.98, ev, va='center', fontsize=10, color=INK2, linespacing=1.55)
        box(ax, 11.1, y, 2.9, 1.95, NEU_SOFT, NEU_SOFT)
        ax.text(12.55, y + 0.98, fate, ha='center', va='center', fontsize=11, weight='bold', color=INK, linespacing=1.35)
        for x0, x1 in ((3.1, 3.3), (10.9, 11.1)):
            ax.annotate('', xy=(x1, y + 0.98), xytext=(x0, y + 0.98),
                        arrowprops=dict(arrowstyle='-|>', color=INK3, lw=1.1, mutation_scale=11))
    y = 0.6
    box(ax, 0.1, y, 13.9, 1.95, WARN_SOFT, WARN, lw=1.4)
    ax.text(0.3, y + 1.6, '仍未回答的部分', fontsize=11, weight='bold', color=WARN)
    ax.text(0.3, y + 0.8,
            '"可接触界面面积和化学降解之间的最优平衡尚未定量确立" [W7220709382]。现有结果方向不一：\n'
            '高比表面积碳分解多、循环差 [W7124424515]；有意利用分解、自限生长时可稳定循环 [W7124464532]；添加剂覆盖度存在最优点 [W7167073746]。\n'
            '已有研究不等于已有选择规则：还不能在动手前判断某个配置该抑制还是该利用。目前看不出另外两个体系能补什么；\n'
            '若按"有条件、可检验的设计判断"来做，终点必须是事先声明的选择加实验检验，不能停在解释文献分歧（否则与课题二重合）。',
            va='center', fontsize=10, color=INK, linespacing=1.6)
    box(ax, 14.3, 0.6, 2.6, 6.45, ACCENT_SOFT, ACCENT, lw=1.6)
    ax.text(15.6, 5.9, '判定', ha='center', fontsize=12.5, weight='bold', color=ACCENT)
    ax.text(15.6, 4.75, 'F 保留为\n重要研究问题', ha='center', va='center', fontsize=13, weight='bold', color=ACCENT,
            linespacing=1.4)
    ax.text(15.6, 2.45, '原设想的两条\n跨体系增量\n暂不成立；\n是否继续取决于\n课题一是否必须\n以跨体系迁移\n为核心贡献', ha='center', va='center',
            fontsize=10.5, color=INK2, linespacing=1.5)
    fig.savefig(out, bbox_inches='tight', facecolor=BG)
    plt.close(fig)


if __name__ == '__main__':
    d = Path(sys.argv[1])
    summ = json.loads((d / 'F_汇总.json').read_text(encoding='utf-8'))
    fig_stance(summ, d / '图3_F立场随年份.png')
    fig_verdict(d / '图4_F核查结论.png')
    print('ok')
