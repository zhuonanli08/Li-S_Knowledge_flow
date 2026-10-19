"""把 _inventory.json 写成交付物：
- 方法清单_复核表.xlsx（只含适用结果）
- 不适用_单独存/不适用结果.xlsx（不适用的方法行与论文，单独存放）
- 图1_三体系方法清单.png / .svg
"""
import json, re, sys, collections
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, PowerNorm
from common import OUT, SCOPES
from build_inventory import VOCAB, GENERIC, COMPONENTS

sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open(OUT / '_inventory.json', encoding='utf-8'))
audit = json.load(open(OUT / 'audit_verdicts.json', encoding='utf-8'))
sample = json.load(open(OUT / '_final_audit_sample.json', encoding='utf-8'))
rows, na_rows, na_papers, uncl = d['rows'], d['na_rows'], d['na_papers'], d['unclassified']
CLASSES = [v for v in VOCAB if v[0] != 'X01']
SHOW = ['液态锂硫', '固态锂金属', '固态锂硫', '固态锂硫_全部年份']
LABEL = {'液态锂硫': '液态锂硫', '固态锂金属': '固态锂金属', '固态锂硫': '固态锂硫·讲动力学', '固态锂硫_全部年份': '固态锂硫·全部年份'}
na_by_scope = collections.Counter(p['范围'] for p in na_papers)
N = {s: d['scope_n'][s] - na_by_scope[s] for s in SHOW}  # 分母扣除不适用论文

papers = collections.defaultdict(set)
for r in rows:
    papers[(r['范围'], r['类别编号'])].add(r['编号'])


def snip(s, ph, w=110):
    i = s.find(ph)
    if i < 0:
        return s[:2 * w]
    return ('…' if i > w else '') + s[max(0, i - w):i] + '【' + ph + '】' + s[i + len(ph):i + len(ph) + w] + ('…' if i + len(ph) + w < len(s) else '')


def reps(scope, code, k=3):
    rs = [r for r in rows if r['范围'] == scope and r['类别编号'] == code]
    rs.sort(key=lambda r: (r['证据来源'] == '做法句', r['年份']), reverse=True)
    out, seen = [], set()
    for r in rs:
        if r['编号'] in seen:
            continue
        seen.add(r['编号'])
        out.append(f"[{r['年份']}] {r['DOI']}：{snip(r['原句（规范化）'], r['命中短语'], 90)}")
        if len(out) == k:
            break
    return '\n'.join(out)


def materials(scope, code, k=8):
    c = collections.Counter()
    for r in rows:
        if r['范围'] == scope and r['类别编号'] == code and r['材料线索（机器抽取）']:
            c.update(t for t in r['材料线索（机器抽取）'].split('、') if t.upper() not in GENERIC)
    return '、'.join(f'{t}({n})' for t, n in c.most_common(k))


def comps(scope, code):
    c = collections.Counter(r['改的组分'] for r in rows if r['范围'] == scope and r['类别编号'] == code)
    return '；'.join(f'{k} {v}' for k, v in c.most_common())


def positions(scope, code):
    c = collections.Counter()
    for r in rows:
        if r['范围'] == scope and r['类别编号'] == code:
            for p in r['作用位置（按命中句）'].split('+'):
                c[p] += 1
    return '；'.join(f'{k} {v}' for k, v in c.most_common())


# 验收轮抽查按类别汇总
ver = audit['验收轮_20261020']['verdicts']
aud = collections.defaultdict(collections.Counter)
for i, r in enumerate(sample):
    if r['抽查组'] != '适用':
        continue
    aud[r['类别编号']][ver.get(str(i), ['✅'])[0]] += 1

# ---------------- 复核表（适用） ----------------
wb = Workbook()
ws = wb.active
ws.title = '说明'
acc = audit['验收轮_20261020']
lines = [
    ('方法清单复核表（第 ② 步）', True),
    ('主问题：固态锂硫正极的硫转化动力学受限。本表只列"三个体系各自用了哪些方法"，不判断能否复用（第 ③ 步）。', False),
    ('', False),
    ('范围（与问题共现分析同一语料 corpus.json）', True),
    (f"液态锂硫：2023–2026 摘要讨论反应/转化动力学的 {d['scope_n']['液态锂硫']} 篇，扣除不适用论文 {na_by_scope['液态锂硫']} 篇后 {N['液态锂硫']} 篇", False),
    (f"固态锂金属：2023–2026 摘要讨论离子传输、界面接触或界面阻抗的 {N['固态锂金属']} 篇", False),
    (f"固态锂硫·讲动力学：2023–2026 摘要讨论反应/转化动力学的 {N['固态锂硫']} 篇（本问题下已用的方法）", False),
    (f"固态锂硫·全部年份：2010–2026 全部 {d['scope_n']['固态锂硫_全部年份']} 篇，扣除不适用 {na_by_scope['固态锂硫_全部年份']} 篇后 {N['固态锂硫_全部年份']} 篇（查某类方法是否出现过）", False),
    ('', False),
    ('怎么识别', True),
    ('只看标题和"本文做法"句（Here/Herein、we propose/design/develop、this work 等），减少把背景提及当成本文实施。', False),
    ('17 个方法类别按"转化为什么慢"的四条原因分组；一篇可属多类。词表与例外规则见"词表"页和 build_inventory.py。', False),
    ('作用位置按命中句判断（先去掉"lithium metal batteries""lithium–sulfur batteries"等电池名）。', False),
    ('', False),
    ('两个维度：方法类别 / 原因（针对转化慢的哪条原因）× 改的组分（改在正极、电解质还是界面）', True),
    ('改的组分：正极·材料（活性物、宿主、负载的催化剂和介体、混合导体宿主）；正极·结构与工艺（三相分布、导电网络、梯度、粒径与混合工艺、粘结剂）；'
     '电解质·正极内（catholyte 成分或种类）；电解质·电解质层（隔膜层电解质、液态电解液）；界面（界面层、包覆、界面调节剂、中间层/隔膜修饰）；工况（压力、温度）。', False),
    ('催化剂的定义（10-19 与用户对齐）：负载在硫正极（碳或宿主）上、通过调节硫物种的吸附/脱附（结合强度）降低转化能垒的物质。'
     '电解质里的填料、电解质掺杂即使论文称"催化"，也不算催化剂。', False),
    (f"人工改判 {len(d['reclass'])} 条（固态锂硫：9 篇改电解质的论文移出催化剂类，3 条不在正极内的离子通路行删除，2 篇补电解质改性行；见"
     '"人工改判记录"页）。固态锂硫正极电解质/混合导体类 25 篇的组分按逐篇阅读核定。', False),
    ('组分抽查（种子 20261021，规则判定的 30 条，Claude 判读）：✅19、🔶7、❌4；4 条错误和 4 条边缘已按规则纠正。', False),
    ('', False),
    ('不适用的结果单独存放在 不适用_单独存/不适用结果.xlsx，不在本表：', True),
    ('① 锂负极专用方法（亲锂层、锂宿主、合金负极、锂表面人工 SEI、抑制枝晶）；② 界面层/包覆层/混合导体层只作用在锂负极；③ 命中句只讲锂负极；④ 非锂硫体系（钠/钾/镁等）；⑤ 摘要不涉及硫或锂硫。', False),
    (f"本表适用方法行 {len(rows)} 条；另存不适用方法行 {len(na_rows)} 条、不适用论文 {len(na_papers)} 篇。", False),
    ('', False),
    ('抽查（Claude 判读，用户未复核）', True),
    ('第 1 轮（种子 20261019）用来找错修规则，不计准确率。验收轮（种子 20261020）在最后一次修规则前抽取：', False),
    (f"适用 88 条：✅ {acc['适用']['✅']}、🔶 {acc['适用']['🔶']}、❌ {acc['适用']['❌']}；不适用 12 条全部 ✅；未归类 12 篇中 6 篇是词表漏（已补）。", False),
    ('验收轮 8 条 ❌ 修规则后 7 条已纠正，1 条仍错（W4391229933，负极侧 Li-石墨中间层的形成工艺仍计入"颗粒尺寸与混合/合成工艺"）；修后未再独立抽查。', False),
    ('原句回查：每条原句都在规范化后的标题/摘要中逐字找到（0 条失败）。', False),
    ('', False),
    ('怎么读、不能怎么读', True),
    ('篇数只说明用得多不多，不说明有效；占比的分母是该组范围内的论文数。', False),
    ('"材料线索"是从标题和做法句机器抽取的化学式/缩写，按论文计，不专指该类方法，未核对。', False),
    ('"人工确认✍"列留给你填；Claude 不改。', False),
]
for i, (t, b) in enumerate(lines, 1):
    c = ws.cell(row=i, column=1, value=t)
    c.font = Font(bold=b, size=12 if b else 11)
    c.alignment = Alignment(wrap_text=True, vertical='top')
ws.column_dimensions['A'].width = 140

# 方法清单
ws = wb.create_sheet('方法清单')
head = ['原因', '编号', '方法类别']
for s in SHOW:
    head += [f'{LABEL[s]} 篇数', f'{LABEL[s]} 占比']
head += ['固态锂硫最早出现年份', '改的组分·液态锂硫', '改的组分·固态锂金属', '改的组分·固态锂硫（全部年份）', '固态锂金属·作用位置（行数）',
         '代表材料线索·液态锂硫', '代表材料线索·固态锂金属', '代表材料线索·固态锂硫',
         '代表文献·液态锂硫', '代表文献·固态锂金属', '代表文献·固态锂硫（全部年份）',
         '另存不适用行数', '验收抽查（该类，修规则前）', '人工确认✍']
ws.append(head)
for code, cause, name, _ in CLASSES:
    row = [cause, code, name]
    for s in SHOW:
        n = len(papers[(s, code)])
        row += [n, round(n / N[s], 3)]
    yrs = [r['年份'] for r in rows if r['范围'] == '固态锂硫_全部年份' and r['类别编号'] == code]
    row += [min(yrs) if yrs else ''] + [comps(s, code) for s in ('液态锂硫', '固态锂金属', '固态锂硫_全部年份')] + [positions('固态锂金属', code),
            materials('液态锂硫', code), materials('固态锂金属', code), materials('固态锂硫_全部年份', code),
            reps('液态锂硫', code), reps('固态锂金属', code), reps('固态锂硫_全部年份', code),
            sum(1 for r in na_rows if r['类别编号'] == code),
            '、'.join(f'{k}{v}' for k, v in sorted(aud[code].items())), '']
    ws.append(row)
widths = [14, 6, 34] + [10, 9] * 4 + [10, 24, 24, 24, 28, 30, 30, 30, 70, 70, 70, 9, 12, 14]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w
for c in ws[1]:
    c.font = Font(bold=True)
    c.alignment = Alignment(wrap_text=True, vertical='center')
    c.fill = PatternFill('solid', fgColor='DCE9F7')
for r in ws.iter_rows(min_row=2):
    for c in r:
        c.alignment = Alignment(wrap_text=True, vertical='top')
    for j in range(5, 12, 2):
        r[j - 1].number_format = '0.0%'
ws.freeze_panes = 'D2'

# 逐篇证据（适用）
ws = wb.create_sheet('逐篇证据')
cols = ['范围', '编号', '年份', 'DOI', '标题', '原因', '类别编号', '方法类别', '改的组分', '组分依据', '作用位置（按命中句）', '命中短语',
        '证据来源', '原句（规范化）', '原句回查', '材料线索（机器抽取）']
ws.append(cols + ['人工确认✍'])
for r in sorted(rows, key=lambda r: (SHOW.index(r['范围']), r['类别编号'], -r['年份'])):
    ws.append([r[k] for k in cols] + [''])
for i, w in enumerate([12, 13, 6, 26, 50, 12, 6, 26, 14, 12, 14, 18, 7, 90, 6, 30, 10], 1):
    ws.column_dimensions[get_column_letter(i)].width = w
for c in ws[1]:
    c.font = Font(bold=True)
ws.freeze_panes = 'C2'
ws.auto_filter.ref = ws.dimensions

# 组分 × 原因（长表）
CAUSES = ['反应本身慢', '电子到不了反应面', '离子到不了反应面', '接触丢失']
ws = wb.create_sheet('组分×原因')
ws.append(['体系', '改的组分', '针对的原因', '论文篇数', '占该组比例', '主要方法类别（篇数）'])
for s in SHOW:
    for comp in COMPONENTS:
        for cause in CAUSES:
            rs = [r for r in rows if r['范围'] == s and r['改的组分'] == comp and r['原因'] == cause]
            ps = {r['编号'] for r in rs}
            if not ps:
                continue
            top = collections.Counter(r['方法类别'] for r in rs)
            ws.append([LABEL[s], comp, cause, len(ps), round(len(ps) / N[s], 3),
                       '；'.join(f'{k}（{v}）' for k, v in top.most_common(3))])
for i, w in enumerate([18, 16, 18, 9, 10, 90], 1):
    ws.column_dimensions[get_column_letter(i)].width = w
for c in ws[1]:
    c.font = Font(bold=True)
for r in ws.iter_rows(min_row=2):
    r[4].number_format = '0.0%'
ws.freeze_panes = 'C2'
ws.auto_filter.ref = ws.dimensions

# 人工改判记录
ws = wb.create_sheet('人工改判记录')
ws.append(['范围', '编号', 'DOI', '标题', '原类别', '处理', '理由', '依据'])
for x in d['reclass']:
    ws.append([x['范围'], x['编号'], x['DOI'], x['标题'], x['原类别'], x['处理'], x['理由'], x['依据']])
for i, w in enumerate([14, 13, 26, 60, 8, 14, 60, 30], 1):
    ws.column_dimensions[get_column_letter(i)].width = w
for c in ws[1]:
    c.font = Font(bold=True)

# 未归类（适用范围内、没识别出方法；只命中负极专用的已在不适用文件里）
ws = wb.create_sheet('未归类_待看')
ws.append(['范围', '编号', '年份', 'DOI', '标题', '做法句', '人工确认✍'])
for u in uncl:
    if u['只命中负极专用']:
        continue
    ws.append([u['范围'], u['编号'], u['年份'], u['DOI'], u['标题'], u['做法句'], ''])
for i, w in enumerate([12, 13, 6, 26, 60, 100, 10], 1):
    ws.column_dimensions[get_column_letter(i)].width = w
for c in ws[1]:
    c.font = Font(bold=True)
ws.freeze_panes = 'C2'
ws.auto_filter.ref = ws.dimensions

# 抽查记录（验收轮）
ws = wb.create_sheet('抽查记录_验收轮')
ws.append(['序号', '抽查组', '范围', '编号', '类别编号', '作用位置', '原句截取 / 标题', '判定', '说明'])
for i, r in enumerate(sample):
    v = ver.get(str(i))
    if r['抽查组'] == '未归类':
        text = r['标题'] + ' || ' + r['做法句'][:200]
        verdict = v or ['—', '见说明页未归类汇总']
        ws.append([i, r['抽查组'], r['范围'], r['编号'], '', '', text, verdict[0], verdict[1]])
    else:
        verdict = v or ['✅', '']
        ws.append([i, r['抽查组'], r['范围'], r['编号'], r['类别编号'], r['作用位置（按命中句）'],
                   snip(r['原句（规范化）'], r['命中短语'], 100), verdict[0], verdict[1]])
for i, w in enumerate([6, 9, 12, 13, 7, 14, 100, 6, 50], 1):
    ws.column_dimensions[get_column_letter(i)].width = w
for c in ws[1]:
    c.font = Font(bold=True)

# 词表
ws = wb.create_sheet('词表')
ws.append(['编号', '原因', '方法类别', '正则（作用于规范化小写的标题和做法句）'])
for v in VOCAB:
    ws.append(list(v))
ws.append([])
ws.append(['', '', '例外规则', '见 build_inventory.py 的 match_classes()：如固态组裸 additive 不算电解液调控、液态组聚合物须有电解质语境、宿主/集流体须有负极语境才算负极专用等'])
for i, w in enumerate([6, 14, 40, 160], 1):
    ws.column_dimensions[get_column_letter(i)].width = w
wb.save(OUT / '方法清单_复核表.xlsx')

# ---------------- 不适用（单独存） ----------------
na_dir = OUT / '不适用_单独存'
na_dir.mkdir(exist_ok=True)
wb = Workbook()
ws = wb.active
ws.title = '说明'
for i, t in enumerate([
    '不适用于现行主线（固态锂硫正极硫转化动力学受限）的方法清单结果，单独存放，不与适用结果混在一起。',
    '不适用规则（事先写入 build_inventory.py，不是事后挑选）：',
    '① 锂负极专用方法（亲锂层、锂宿主、合金负极、锂表面人工 SEI、抑制枝晶）',
    '② 界面层/包覆层/混合导体层只作用在锂负极（命中句讲负极、未涉及正极）',
    '③ 命中句只讲锂负极（无正极、电解质或隔膜语境）',
    '④ 非锂硫体系（钠/钾/镁/铝/钙）  ⑤ 摘要不涉及硫或锂硫（多为电解质材料或锂负极研究）',
    f'方法行 {len(na_rows)} 条（同一篇论文的其他适用方法仍在复核表里）；论文 {len(na_papers)} 篇（整篇不进复核表）。',
    '验收抽查 12 条不适用行全部判对（Claude 判读，用户未复核）。',
], 1):
    ws.cell(row=i, column=1, value=t).alignment = Alignment(wrap_text=True)
ws.column_dimensions['A'].width = 120
ws = wb.create_sheet('不适用方法行')
cols2 = ['范围', '编号', '年份', 'DOI', '标题', '类别编号', '方法类别', '作用位置（按命中句）', '命中短语', '原句（规范化）', '不适用原因']
ws.append(cols2)
for r in na_rows:
    ws.append([r[k] for k in cols2])
for i, w in enumerate([12, 13, 6, 26, 50, 6, 26, 14, 18, 90, 40], 1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.auto_filter.ref = ws.dimensions
ws = wb.create_sheet('不适用论文')
cols3 = ['范围', '编号', '年份', 'DOI', '标题', '不适用原因', '原句']
ws.append(cols3)
for p in na_papers:
    ws.append([p[k] for k in cols3])
for i, w in enumerate([12, 13, 6, 26, 60, 36, 90], 1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws = wb.create_sheet('按类别计数')
ws.append(['类别编号', '方法类别'] + SHOW)
for code, cause, name, _ in VOCAB:
    ws.append([code, name] + [sum(1 for r in na_rows if r['类别编号'] == code and r['范围'] == s) for s in SHOW])
for ws_ in wb.worksheets[1:]:
    for c in ws_[1]:
        c.font = Font(bold=True)
wb.save(na_dir / '不适用结果.xlsx')

# ---------------- 图 ----------------
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
INK, INK2, MUTED, SURF = '#0b0b0b', '#52514e', '#898781', '#fcfcfb'
ramp = ['#f3f7fd', '#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
cmap = LinearSegmentedColormap.from_list('blue', ramp)
norm = PowerNorm(gamma=0.5, vmin=0, vmax=0.6)

nrow, ncol = len(CLASSES), len(SHOW)
fig, ax = plt.subplots(figsize=(13.5, 12.5), dpi=200)
fig.patch.set_facecolor(SURF)
ax.set_facecolor(SURF)
causes = [c for c in ['反应本身慢', '电子到不了反应面', '离子到不了反应面', '接触丢失']]
y = 0
ypos = {}
for cause in causes:
    for code, cs, name, _ in CLASSES:
        if cs == cause:
            ypos[code] = y
            y += 1
    y += 0.45  # 组间留白
total_h = y - 0.45
for code, cs, name, _ in CLASSES:
    yy = ypos[code]
    for j, s in enumerate(SHOW):
        n = len(papers[(s, code)])
        share = n / N[s]
        col = cmap(norm(share)) if n else '#efeeea'
        ax.add_patch(plt.Rectangle((j + 0.03, yy + 0.04), 0.94, 0.92, facecolor=col, edgecolor=SURF, linewidth=2))
        txt = f'{n}\n{share * 100:.1f}%' if n else '0'
        tc = '#ffffff' if norm(share) > 0.55 else INK
        ax.text(j + 0.5, yy + 0.5, txt, ha='center', va='center', fontsize=9.5, color=tc, linespacing=1.15)
    ax.text(-0.08, yy + 0.5, name.replace('₂', '2'), ha='right', va='center', fontsize=10, color=INK)
for cause in causes:
    ys = [ypos[c] for c, cs, _, _ in CLASSES if cs == cause]
    ax.text(-3.55, (min(ys) + max(ys) + 1) / 2, cause, ha='center', va='center', fontsize=11, color=INK2,
            fontweight='bold', rotation=90)
    ax.plot([-3.3, -3.3], [min(ys) + 0.1, max(ys) + 0.9], color=MUTED, linewidth=1.2, clip_on=False)
for j, s in enumerate(SHOW):
    ax.text(j + 0.5, -0.35, f'{LABEL[s]}\nn={N[s]}', ha='center', va='bottom', fontsize=10.5, color=INK, fontweight='bold')
ax.set_xlim(-3.8, ncol)
ax.set_ylim(total_h + 0.2, -1.6)
ax.axis('off')
fig.text(0.02, 0.975, '固态锂硫正极硫转化动力学受限：三个体系各用了哪些方法', fontsize=16, fontweight='bold', color=INK, va='top')
fig.text(0.02, 0.952, '格内为论文篇数与占该组比例；只从标题和"本文做法"句识别，一篇可属多类；篇数不代表方法有效，也不代表能复用。',
         fontsize=10, color=INK2, va='top')
fig.text(0.02, 0.022, f"范围：液态锂硫、固态锂硫·讲动力学 = 2023–2026 摘要讨论反应/转化动力学的论文；固态锂金属 = 2023–2026 讨论离子传输/接触/界面阻抗的论文；"
         f"固态锂硫·全部年份 = 2010–2026 全部。\n锂负极专用方法、只作用于锂负极的界面层、非锂硫论文已单独存放，不在图中。"
         f"验收抽查：适用 88 条中正确 {acc['适用']['✅']}、边缘 {acc['适用']['🔶']}、错误 {acc['适用']['❌']}（错误中 7 条已修；Claude 判读，用户未复核）。",
         fontsize=8.5, color=MUTED, va='bottom')
cax = fig.add_axes([0.80, 0.905, 0.17, 0.012])
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
cb = fig.colorbar(sm, cax=cax, orientation='horizontal', ticks=[0, 0.05, 0.2, 0.4, 0.6])
cb.ax.set_xticklabels(['0', '5%', '20%', '40%', '60%'], fontsize=8, color=INK2)
cb.outline.set_visible(False)
cax.set_title('占该组比例', fontsize=9, color=INK2, pad=3)
plt.subplots_adjust(left=0.03, right=0.98, top=0.90, bottom=0.07)
fig.savefig(OUT / '图1_三体系方法清单.png', facecolor=SURF)
fig.savefig(OUT / '图1_三体系方法清单.svg', facecolor=SURF)
plt.close(fig)

# ---------------- 图 2：改的组分 × 针对的原因 ----------------
PANELS = ['液态锂硫', '固态锂金属', '固态锂硫_全部年份']
CAUSE_SHORT = ['反应\n本身慢', '电子\n到不了', '离子\n到不了', '接触\n丢失']
fig, axes = plt.subplots(1, 3, figsize=(15, 6.6), dpi=200)
fig.patch.set_facecolor(SURF)
for k, (ax, s) in enumerate(zip(axes, PANELS)):
    ax.set_facecolor(SURF)
    for i, comp in enumerate(COMPONENTS):
        for j, cause in enumerate(CAUSES):
            n = len({r['编号'] for r in rows if r['范围'] == s and r['改的组分'] == comp and r['原因'] == cause})
            share = n / N[s]
            col = cmap(norm(share)) if n else '#efeeea'
            ax.add_patch(plt.Rectangle((j + 0.03, i + 0.04), 0.94, 0.92, facecolor=col, edgecolor=SURF, linewidth=2))
            if n:
                tc = '#ffffff' if norm(share) > 0.55 else INK
                ax.text(j + 0.5, i + 0.5, f'{n}\n{share * 100:.1f}%', ha='center', va='center', fontsize=9, color=tc, linespacing=1.1)
        if k == 0:
            ax.text(-0.1, i + 0.5, comp, ha='right', va='center', fontsize=10.5, color=INK)
    for j, c in enumerate(CAUSE_SHORT):
        ax.text(j + 0.5, -0.12, c, ha='center', va='bottom', fontsize=9.5, color=INK2)
    ax.text(2, -1.05, f'{LABEL[s]}（n={N[s]}）', ha='center', va='bottom', fontsize=12, color=INK, fontweight='bold')
    ax.set_xlim(-0.05 if k else -2.6, 4.05)
    ax.set_ylim(len(COMPONENTS) + 0.05, -1.3)
    ax.axis('off')
fig.text(0.015, 0.975, '改在哪里 × 针对哪条原因：三个体系的方法分布', fontsize=15, fontweight='bold', color=INK, va='top')
fig.text(0.015, 0.935, '格内为论文篇数与占该组比例；"改的组分"按正极 / 电解质 / 界面三分，催化剂按"负载在硫正极、调节硫物种吸附脱附"计入正极·材料。',
         fontsize=9.5, color=INK2, va='top')
fig.text(0.015, 0.02, '范围同图 1；液态锂硫、固态锂金属为 2023–2026，固态锂硫为 2010–2026 全部。组分大部分按规则判定，固态锂硫催化剂与正极电解质/混合导体类按逐篇阅读核定（Claude 判读，用户未复核）。',
         fontsize=8.5, color=MUTED, va='bottom')
cax = fig.add_axes([0.84, 0.905, 0.14, 0.014])
cb = fig.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=norm), cax=cax, orientation='horizontal', ticks=[0, 0.05, 0.2, 0.4, 0.6])
cb.ax.set_xticklabels(['0', '5%', '20%', '40%', '60%'], fontsize=8, color=INK2)
cb.outline.set_visible(False)
plt.subplots_adjust(left=0.10, right=0.99, top=0.83, bottom=0.07, wspace=0.05)
fig.savefig(OUT / '图2_组分×原因.png', facecolor=SURF)
fig.savefig(OUT / '图2_组分×原因.svg', facecolor=SURF)
print('输出完成：复核表适用行', len(rows), '；不适用行', len(na_rows), '不适用论文', len(na_papers), '；人工改判', len(d['reclass']))
