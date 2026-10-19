from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

OUT=Path(__file__).resolve().parent
pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/msyh.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('CNB','C:/Windows/Fonts/msyhbd.ttc',subfontIndex=0))
INK='#203448'; BLUE='#236586'; GREEN='#287768'; GRAY='#596773'; ORANGE='#916126'

class Figure:
    def __init__(self,name,w,h):
        self.name,self.w,self.h=name,w,h
        self.c=canvas.Canvas(str(OUT/(name+'.pdf')),pagesize=(w,h))
        self.c.setTitle(name); self.c.setAuthor('Research workflow based on local Scheme D')
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">', '<rect width="100%" height="100%" fill="white"/>']
    def rect(self,x,y,w,h,fill='#FFFFFF',stroke='#BCC9D2'):
        c=self.c;c.setFillColor(HexColor(fill));c.setStrokeColor(HexColor(stroke));c.setLineWidth(1)
        c.rect(x,self.h-y-h,w,h,fill=1,stroke=1)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}"/>')
    def text(self,x,y,s,size=14,color=INK,bold=False):
        c=self.c;c.setFont('CNB' if bold else 'CN',size);c.setFillColor(HexColor(color));c.drawString(x,self.h-y-size,s)
        self.svg.append(f'<text x="{x}" y="{y+size*.88}" font-family="Microsoft YaHei, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(s)}</text>')
    def lines(self,x,y,lines,size=14,color=INK,leading=23):
        for i,s in enumerate(lines):self.text(x,y+i*leading,s,size,color)
    def line(self,x1,y1,x2,y2,color=GRAY,dash=False):
        c=self.c;c.setStrokeColor(HexColor(color));c.setLineWidth(1.2);c.setDash([4,3] if dash else [])
        c.line(x1,self.h-y1,x2,self.h-y2);c.setDash([])
        self.svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.2"'+(' stroke-dasharray="4 3"' if dash else '')+'/>')
    def arrow(self,x1,y1,x2,y2):
        self.line(x1,y1,x2,y2)
        import math
        a=math.atan2(y2-y1,x2-x1)
        for d in [-.5,.5]:self.line(x2,y2,x2-7*math.cos(a+d),y2-7*math.sin(a+d))
    def box(self,x,y,w,h,title,lines,color=BLUE,fill='#F2F7FA'):
        self.rect(x,y,w,h,fill,color);self.text(x+16,y+12,title,17,color,True);self.lines(x+16,y+42,lines,14)
    def save(self):
        self.c.showPage();self.c.save();self.svg.append('</svg>')
        (OUT/(self.name+'.svg')).write_text('\n'.join(self.svg),encoding='utf-8')

f=Figure('项目流程图_论文主图',1000,1110)
f.text(40,25,'三体系设计经验的复用、改造与组合：研究流程',25,bold=True)
f.text(40,66,'研究对象：以固态锂硫为目标，比较非硫固态与液态锂硫的相关设计经验',14,GRAY)
for x,title,body in [(40,'非硫固态',['固态电解质 + 非硫正极','固态界面、传输、力学与加工']), (350,'固态锂硫',['固态电解质 + 硫基正极','目标体系；核实最终液相状态']), (660,'液态锂硫',['液态电解液 + 硫基正极','硫反应、物种调控与电极设计'])]:
    f.box(x,104,300,102,title,body)
for x in [190,500,810]:f.line(x,206,x,222)
f.line(190,222,810,222);f.arrow(500,222,500,244)
f.box(180,244,640,100,'01  语料整理与质量控制',['记录检索范围、日期、去重、文献类型及分组依据','核实主统计纳入条件；单列支撑研究、含液/凝胶与待核实记录'])
f.arrow(500,344,500,368)
f.box(180,368,640,100,'02  摘要层：识别跨体系分布差异',['标注问题、策略、角色与位置；经独立人工验证后开展全量统计','按体系和时段比较比例与不确定性，形成问题/策略分布图'])
f.arrow(500,468,500,492)
f.box(180,492,640,100,'03  筛选具体功能问题',['综合目标需求、两侧策略、已有证据、数据可得性与实验可区分性','选定主问题；全文范围聚焦正极、电解质及其相互作用界面'])
f.arrow(500,592,500,616)
f.box(180,616,640,112,'04  全文层：建立适用性证据与可检验假设',['样品 → 测试 → 对照比较；区分实测观察、作者解释与新假设','判定单位：具体策略实现 × 明确的固态锂硫目标配置','材料/局部界面相近，或功能需求相近；逐项核对关键条件'])
for x in [195,500,805]:
    f.line(500,728,500,741);f.line(195,741,805,741);f.arrow(x,741,x,760)
f.box(40,760,310,102,'复用候选',['关键条件匹配','实验：基线 vs 策略'],GREEN,'#F1F7F4')
f.box(365,760,270,102,'改造候选',['有证据显示条件不匹配','基线 / 原策略 / 改造后'],GREEN,'#F1F7F4')
f.box(650,760,310,102,'组合假设（有依据时）',['文献支持互补或限制假设','基线 / 甲 / 乙 / 甲+乙'],GREEN,'#F1F7F4')
for x in [195,500,805]:f.line(x,862,x,898)
f.line(195,898,805,898);f.arrow(500,898,500,928)
f.box(180,928,640,86,'05  实验层：检验效果及机制',['独立重复与不确定性 + 性能评价 + 界面、结构或反应表征','产出：分布图谱、适用性证据库、复用/改造原则及实验验证'],GREEN,'#F1F7F4')
f.text(40,1030,'注：三组比较用于描述，不分离固态与硫的因果效应；相似策略不等于已发生知识迁移。',12,GRAY)
f.text(40,1050,'组合实验以策略能独立操控为前提；图示为研究设计，不表示所有阶段已完成。',12,GRAY)
f.text(40,1070,'证据不足：记适用性未知并补证据；明确不适用：不进入当前配置的实验验证。',12,ORANGE)
f.save()

g=Figure('项目流程图_数据进度与局限',1400,1110)
g.text(36,24,'项目执行图：每一步做什么、需要什么、目前卡在哪里',26,bold=True)
g.text(36,66,'依据方案 D（2026-10-18）及试点计划；状态为文档记载，未重新盘点数据库或核验工作簿。',14,GRAY)
cols=[(36,300,'所需数据'),(356,450,'研究步骤与输出'),(826,538,'当前进度 / 局限与控制')]
for x,w,t in cols:g.rect(x,100,w,37,'#203448','#203448');g.text(x+12,106,t,17,'#FFFFFF',True)
rows=[
('01  语料与分组核查',
 ['论文号、DOI、年份、标题摘要','检索命中与补池记录','文献类型、配置、液相状态'],
 ['核对三体系边界与主统计纳入条件','支撑研究、含液/凝胶、待核实单列','输出：可追溯论文表与纳排记录'],
 ['待完成：随机60篇核查及定向排查，提交复核。','旧组名不能直接等同于方案D的新边界。','随机与定向样本分开报告；组内核查不估计漏收。']),
('02  摘要标注与描述统计',
 ['符合纳入条件的原创论文摘要','问题/策略词表、角色与位置','开发样本及独立人工验证集'],
 ['标注 → 独立核验 → 全量统计','按体系、时段汇总论文级比例','输出：问题关注与策略使用分布图'],
 ['已完成首批60篇试点；不代表全量标注已完成。','文档缺摘要约23%–37%；旧分组仍待核查。','摘要未提及 ≠ 不存在；三组非完整四格因子设计。']),
('03  候选问题筛选',
 ['分布差异及对应原文','目标体系需求、已有应用证据','全文可得性及实验室能力'],
 ['逐项说明选择理由，不计算总分','聚焦正极—电解质相关的具体问题','输出：主问题及进入深读的候选清单'],
 ['待定：第二层主问题与主实验。','关注度差异不能直接证明空白或实验价值。','不预设导电碳包覆优先；H01仅为试点候选。']),
('04  全文证据抽取',
 ['选定问题的正文与补充材料','样品、配方、加工与测试条件','对照、性能、表征、误差及定位'],
 ['样品 → 测试 → 比较（实测观察）','策略页记录作者解释与作用前提','输出：六页关联证据表及来源记录'],
 ['已完成5篇表样；须按v0.2回填并实质复核。','44行“需人看”；原句匹配不等于科学判断正确。','条件缺失记未知；原文数值/单位冲突保留待核。']),
('05  适用性判定与组合假设',
 ['具体策略实现及支持的比较','明确目标配置、前提与证据','固态锂硫已有应用及反例'],
 ['匹配 → 复用；不匹配 → 改造/不适用','不足 → 未知；互补/限制另建组合假设','输出：可检验假设及候选实验设计'],
 ['尚未形成经核验的正式适用性结论。','相同材料不保证相同效果；功能类比仍是假设。','性能改善证据与机制证据分开，避免因果过推。']),
('06  实验验证与结论',
 ['实验材料、加工与测试平台','基线及策略组、独立重复','预设指标、尺度和机制表征'],
 ['复用：2组；改造：3组','可独立操控的组合：2×2四组','输出：效果、交互及机制支持程度'],
 ['待候选比较与实验能力确认；文档未报告完成。','组合交互需重复与不确定性，不能只看单次结果。','负交互不直接证明化学冲突；结论限定目标配置。'])]
for i,(title,left,mid,right) in enumerate(rows):
    y=151+i*135
    g.rect(36,y,300,115,'#F8FAFB');g.lines(49,y+17,left,15,leading=27)
    g.box(356,y,450,115,title,mid)
    g.rect(826,y,538,115,'#FFF9F1','#D8C5A9');g.lines(840,y+16,right,15,leading=28)
    g.arrow(336,y+57,356,y+57)
    if i<5:g.arrow(581,y+115,581,y+135)
g.rect(36,973,1328,94,'#F1F7F4','#287768')
g.text(51,984,'当前优先顺序',17,GREEN,True)
g.lines(215,984,['固定词表与表结构 → 分组核查 + 现有5篇回填 → 提交复核 → 再做批2与候选比较。',
                       '全文约30篇、实验1–3个均是工作量规划，不是已经完成的样本量或结果。'],16,leading=29)
g.text(36,1080,'阅读提示：左列是输入，中列是处理及产出，右列是证据边界。历史引用分析不进入方案D主线。',13,GRAY)
g.save()
