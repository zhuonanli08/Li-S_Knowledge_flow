"""Three-system comparisons on shared canvases. No new corpus labels or scores."""
from pathlib import Path
import sys,math,json,collections,itertools,zipfile,hashlib
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT/'_deps'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle,Wedge,FancyArrowPatch,FancyBboxPatch
from matplotlib.lines import Line2D
import networkx as nx

DEST=OUT/'三体系综合图';DEST.mkdir(exist_ok=True)
font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc')
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'svg.fonttype':'none','font.size':11,'figure.facecolor':'white'})
GROUPS=['固态锂硫','液态锂硫','固态锂金属']
C=['#087F8C','#CB752D','#7358A7'];INK='#193348';MUTED='#536B7B';GRAY='#9CAAB3';BG='#F4F7F9'
freq=pd.read_csv(OUT/'问题频率_跨体系与时段.csv')
edges=pd.read_csv(OUT/'共现网络_全部边.csv')
recent=freq[(freq['时段']=='2023-2026')&(freq['口径']=='校正主集')&(freq['模式']=='一般提及')]
ids=sorted(recent['标签号'].unique());labels=recent.drop_duplicates('标签号').set_index('标签号')['主题'].to_dict()
types=recent.drop_duplicates('标签号').set_index('标签号')['类型'].to_dict()
den={g:int(recent[recent['体系']==g]['分母'].iloc[0]) for g in GROUPS}
p=recent.pivot(index='标签号',columns='体系',values='占比')[GROUPS].reindex(ids)
counts=recent.pivot(index='标签号',columns='体系',values='篇数')[GROUPS].reindex(ids)
short={'P01':'离子传输/电导','P02':'电子传输/电导','P03':'反应/转化动力学','P04':'界面接触/润湿','P05':'界面阻抗/传输','P06':'副反应/界面化学','P07':'电位稳定性/窗口','P08':'体积变化/应力','P09':'裂纹/孔洞/结构失效','P10':'枝晶/不均匀沉积','P11':'多硫化物溶解/穿梭','P12':'活性物利用/转化程度','P13':'高载量/厚电极','P14':'压力/力学强度','P15':'室温/温度条件','P16':'空气/水稳定性','P17':'加工/规模化','P18':'热安全/易燃','P19':'少电解液/非活性占比'}

def title(fig,main,sub):
    fig.text(.035,.965,main,fontsize=22,color=INK,weight='bold',va='top')
    fig.text(.035,.915,sub,fontsize=11,color=MUTED,va='top')
def save(fig,name):
    for ext in ['png','svg']:fig.savefig(DEST/f'{name}.{ext}',dpi=220,bbox_inches='tight',facecolor='white')
    plt.close(fig)
def membership(th=.05,mincount=5):
    return {pid:tuple(int(p.loc[pid,g]>=th and counts.loc[pid,g]>=mincount) for g in GROUPS) for pid in ids}
def fmtmask(mask):return ' + '.join(g for g,m in zip(GROUPS,mask) if m) or '三组均未达门槛'

def venn():
    mem=membership();regions=collections.defaultdict(list)
    for pid,m in mem.items():regions[m].append(pid)
    fig=plt.figure(figsize=(16,12.8));ax=fig.add_axes([.045,.12,.74,.73]);ax.set_xlim(-6.7,6.7);ax.set_ylim(-4.6,7.3);ax.set_aspect('equal');ax.axis('off')
    centers=[(0,2.8),(-2.3,0),(2.3,0)]
    for xy,c in zip(centers,C):ax.add_patch(Circle(xy,4.2,facecolor=c,alpha=.09,edgecolor='none'))
    for xy,c in zip(centers,C):ax.add_patch(Circle(xy,4.2,fill=False,edgecolor=c,lw=2,alpha=.75))
    ax.text(0,7.18,'固态锂硫',ha='center',va='bottom',fontsize=20,weight='bold',color=C[0])
    ax.text(-4.9,-4.26,'液态锂硫',ha='center',fontsize=20,weight='bold',color=C[1])
    ax.text(4.9,-4.26,'固态锂金属',ha='center',fontsize=20,weight='bold',color=C[2])
    positions={(1,0,0):(0,5.8),(0,1,0):(-4.8,-.6),(0,0,1):(4.8,-.6),(1,1,0):(-2.6,3.2),(1,0,1):(2.6,3.2),(0,1,1):(0,-2.8),(1,1,1):(0,.65)}
    names={(1,0,0):'仅固态锂硫达门槛',(0,1,0):'仅液态锂硫达门槛',(0,0,1):'仅固态锂金属达门槛',(1,1,0):'两类锂硫共同关注',(1,0,1):'两类固态共同关注',(0,1,1):'液态锂硫 + 固态锂金属',(1,1,1):'三体系共同关注'}
    for mask,(x,y) in positions.items():
        members=regions[mask];fs=12 if sum(mask)!=1 else 10.5
        ax.text(x,y+.52,names[mask],ha='center',va='bottom',fontsize=fs,weight='bold',color=INK)
        content='\n'.join(short[pid] for pid in members) if members else '无'
        if mask==(0,1,0):content='少电解液 /\n非活性占比'
        if mask==(0,0,1):content='裂纹 / 孔洞 /\n结构失效\n热安全 / 易燃'
        ax.text(x,y+.38,content,ha='center',va='top',fontsize=12.5 if sum(mask)>1 else 12,color=INK,linespacing=1.7)
    # Exact presence is shown separately; threshold membership is not existence.
    side=fig.add_axes([.80,.23,.18,.56]);side.axis('off')
    side.text(0,.97,'先区分两种“重叠”',fontsize=15,weight='bold',color=INK,va='top')
    side.text(0,.85,'按至少检出1篇：',fontsize=12,weight='bold',color=INK,va='top')
    side.text(0,.79,'18类主题\n三体系均有提及',fontsize=15,color=C[0],linespacing=1.6,va='top')
    side.text(0,.63,'多硫化物溶解/穿梭\n只在两类锂硫中检出；\n固态锂金属为0篇。',fontsize=11.5,color=MUTED,linespacing=1.6,va='top')
    side.text(0,.40,'主图按“较常关注”：',fontsize=12,weight='bold',color=INK,va='top')
    side.text(0,.33,'组内提及率 ≥ 5%\n且命中 ≥ 5篇。\n圆外只表示未达门槛，\n不表示没有该问题。',fontsize=11.5,color=MUTED,linespacing=1.7,va='top')
    title(fig,'三体系的问题关注在哪里重叠？','2023—2026年摘要；固态锂硫 n=289，液态锂硫 n=3,109，固态锂金属 n=2,440。')
    fig.text(.035,.082,'三组均未达5%门槛：空气/水稳定性（固态锂硫1.0%、液态锂硫0.1%、固态锂金属2.7%）。',fontsize=11,color=MUTED)
    fig.text(.035,.052,'集合表示主题类别，不是论文集合；圆面积不编码数量。副反应在液态锂硫为4.7%，接近门槛，不能解释成“没有”。',fontsize=10.5,color=MUTED)
    fig.text(.035,.025,'阈值仅帮助阅读关注分布；1%、3%、5%、10%的归类对照随图提供。主题含机制问题及工况/工程约束。',fontsize=10.5,color=MUTED)
    save(fig,'05_三体系问题重叠图')
    rows=[]
    for pid in ids:
        rr={'标签号':pid,'主题':labels[pid],'类型':types[pid]}
        for g in GROUPS:rr[g+'篇数']=int(counts.loc[pid,g]);rr[g+'提及率']=float(p.loc[pid,g])
        rr['至少1篇的检出组']=fmtmask(tuple(int(counts.loc[pid,g]>0) for g in GROUPS))
        for th in [.01,.03,.05,.10]:rr[f'{th:.0%}且至少5篇']=fmtmask(membership(th)[pid])
        rows.append(rr)
    pd.DataFrame(rows).to_csv(DEST/'主题重叠及阈值敏感性.csv',index=False,encoding='utf-8-sig')

def build_edges(th=.25):
    selected={};allvals={}
    base=edges[(edges['时段']=='2023-2026')&(edges['模式']=='一般提及')&(edges['A']<='P12')&(edges['B']<='P12')]
    for (a,b),block in base.groupby(['A','B']):
        by=block.set_index('体系');mask=[]
        for g in GROUPS:
            r=by.loc[g];mask.append(bool(r['共现篇数']>=max(5,math.ceil(.01*den[g])) and r['cosine']>=th))
        allvals[(a,b)]=by
        if any(mask):selected[(a,b)]=tuple(mask)
    return selected,allvals

def network():
    selected,allvals=build_edges();nodeids=[f'P{i:02}' for i in range(1,13)]
    G=nx.Graph();G.add_nodes_from(nodeids)
    for (a,b),m in selected.items():G.add_edge(a,b,weight=float(allvals[(a,b)]['cosine'].mean()))
    # Fixed presentation positions keep all 12 nodes and their labels legible.
    # Distances and placement have no quantitative or clustering interpretation.
    pos={'P01':(-.7,.35),'P02':(.45,-2.3),'P03':(-1.6,-2.5),'P04':(.5,2.4),'P05':(-1.3,3.2),'P06':(3.1,.8),'P07':(2.7,3.0),'P08':(-3.2,1.8),'P09':(3.15,-2.7),'P10':(1.25,-.55),'P11':(-3,-.7),'P12':(-3,-3.2)}
    labelpos={'P01':(-.7,1.28),'P02':(.45,-3.18),'P03':(-1.6,-3.43),'P04':(.5,3.17),'P05':(-1.3,3.96),'P06':(3.4,.02),'P07':(3.0,3.76),'P08':(-3.2,2.55),'P09':(3.15,-3.50),'P10':(1.25,-1.42),'P11':(-3,.23),'P12':(-3,-3.98)}
    pos={n:np.array([x*1.18,y]) for n,(x,y) in pos.items()}
    labelpos={n:(x*1.18,y) for n,(x,y) in labelpos.items()}
    fig=plt.figure(figsize=(16.6,11.5));ax=fig.add_axes([.025,.145,.735,.70]);ax.set_xlim(-5.2,5.2);ax.set_ylim(-4.45,4.45);ax.set_aspect('equal');ax.axis('off')
    for (a,b),m in selected.items():
        gg=[i for i,v in enumerate(m) if v];rads={1:[0],2:[-.045,.045],3:[-.085,0,.085]}[len(gg)]
        for gi,rad in zip(gg,rads):
            cosine=float(allvals[(a,b)].loc[GROUPS[gi],'cosine'])
            ax.add_patch(FancyArrowPatch(pos[a],pos[b],arrowstyle='-',connectionstyle=f'arc3,rad={rad}',linewidth=4*cosine,color=C[gi],alpha=.64,zorder=1))
    radii={n:.58*math.sqrt(float(p.loc[n].mean())/.5) for n in nodeids}
    labeltext={'P01':'离子传输\n电导','P02':'电子传输\n电导','P03':'反应/转化\n动力学','P04':'界面接触\n润湿','P05':'界面阻抗\n传输','P06':'副反应\n界面化学','P07':'电位稳定性\n窗口','P08':'体积变化\n应力','P09':'裂纹/孔洞\n结构失效','P10':'枝晶\n不均匀沉积','P11':'多硫化物\n溶解/穿梭','P12':'活性物利用\n转化程度'}
    for n in sorted(nodeids,key=lambda n:-float(p.loc[n].mean())):
        x,y=pos[n];r=radii[n];start=90
        for gi,g in enumerate(GROUPS):
            angle=float(p.loc[n,g]/p.loc[n].sum())*360
            if angle>0:ax.add_patch(Wedge((x,y),r,start,start+angle,facecolor=C[gi],edgecolor='white',linewidth=.7,zorder=3))
            start+=angle
        tx,ty=labelpos[n]
        if math.hypot(tx-x,ty-y)>r+.5:ax.plot([x,tx],[y,ty],color=GRAY,lw=.7,zorder=2)
        ax.text(tx,ty,labeltext[n],ha='center',va='center',fontsize=12,color=INK,zorder=5,bbox={'facecolor':'white','edgecolor':'none','alpha':.9,'pad':1.5})
    side=fig.add_axes([.775,.17,.20,.66]);side.axis('off')
    side.text(0,.98,'每个问题只出现一次',fontsize=15,weight='bold',color=INK,va='top')
    for gi,g in enumerate(GROUPS):
        side.plot([0,.16],[.88-gi*.065]*2,color=C[gi],lw=3)
        side.text(.21,.88-gi*.065,g,fontsize=12,va='center',color=C[gi])
    side.text(0,.66,'圆的面积：\n三体系提及率的均值\n扇区比例：\n各体系提及率的相对份额',fontsize=11.3,color=MUTED,linespacing=1.55,va='top')
    side.text(0,.44,'同一对问题的多色连线\n表示多个体系都达到了\n共现显示阈值。',fontsize=11.3,color=MUTED,linespacing=1.6,va='top')
    side.text(0,.25,f'{len(selected)} 对共现关系\n{sum(sum(m)>=2 for m in selected.values())} 对在多个体系达门槛\n{sum(sum(m)==3 for m in selected.values())} 对在三体系均达门槛',fontsize=13,weight='bold',color=INK,linespacing=1.65,va='top')
    side.set_xlim(0,1);side.set_ylim(0,1)
    title(fig,'三体系叠在同一张问题共现网络中','2023—2026年；12类机制主题共享一组节点。多色连线显示共现关系在哪些体系中重复出现。')
    fig.text(.035,.103,'每个体系单独计算：cosine ≥ 0.25，且共现 ≥ max(5篇, 组内1%)。粗细反映cosine；无连线不等于没有共现。',fontsize=10.7,color=MUTED)
    fig.text(.035,.067,'节点位置只用于排版，距离不编码相似性。面积和扇区基于组内提及率，不是三组论文数在混合库中的份额。',fontsize=10.7,color=MUTED)
    fig.text(.035,.031,'圆和连线均表示摘要层面的讨论；不表示机制相同、因果关系或方法可直接迁移。',fontsize=10.7,color=MUTED)
    save(fig,'06_三体系共享共现网络')
    rows=[]
    for (a,b),m in selected.items():
        r={'A':a,'B':b,'主题A':labels[a],'主题B':labels[b],'达门槛体系':fmtmask(m),'体系数':sum(m)}
        for gi,g in enumerate(GROUPS):
            vv=allvals[(a,b)].loc[g];r[g+'共现篇数']=int(vv['共现篇数']);r[g+'cosine']=float(vv['cosine']);r[g+'达门槛']=m[gi]
        rows.append(r)
    pd.DataFrame(rows).to_csv(DEST/'共享网络_逐关系数据.csv',index=False,encoding='utf-8-sig')
    net=nx.Graph()
    for n in nodeids:
        net.add_node(n,label=labels[n],x=float(pos[n][0]),y=float(pos[n][1]),**{g+'_提及率':float(p.loc[n,g]) for g in GROUPS})
    for r in rows:
        attrs={k:v for k,v in r.items() if k not in ['A','B']};net.add_edge(r['A'],r['B'],**attrs)
    nx.write_graphml(net,DEST/'三体系共享网络.graphml')
    sense=[]
    for th in [.20,.25,.30]:
        sel,_=build_edges(th);sense.append({'cosine门槛':th,'关系总数':len(sel),'单体系达门槛':sum(sum(m)==1 for m in sel.values()),'两体系达门槛':sum(sum(m)==2 for m in sel.values()),'三体系达门槛':sum(sum(m)==3 for m in sel.values())})
    pd.DataFrame(sense).to_csv(DEST/'网络阈值敏感性.csv',index=False,encoding='utf-8-sig')

def bubble():
    fig=plt.figure(figsize=(17,11.2));ax=fig.add_axes([.075,.18,.57,.65]);ax.set_xlim(-3,62);ax.set_ylim(-6,74)
    ax.axvline(5,color=GRAY,lw=1,ls=(0,(4,4)));ax.axhline(5,color=GRAY,lw=1,ls=(0,(4,4)))
    ax.set_xticks(range(0,61,10));ax.set_yticks(range(0,71,10));ax.grid(alpha=.15);ax.set_axisbelow(True)
    ax.spines['right'].set_visible(False);ax.spines['top'].set_visible(False)
    ax.set_xlabel('液态锂硫中的提及率（%）',fontsize=13,labelpad=12,color=C[1])
    ax.set_ylabel('固态锂金属中的提及率（%）',fontsize=13,labelpad=12,color=C[2])
    coords={pid:(float(p.loc[pid,GROUPS[1]])*100,float(p.loc[pid,GROUPS[2]])*100) for pid in ids}
    # IDs retain exact data coordinates, with leaders to prevent small near-zero points obscuring each other.
    numberpos={'P01':(16.4,64.6),'P02':(15,8.8),'P03':(46,8),'P04':(-1,16),'P05':(-1,10.8),'P06':(4.7,35),'P07':(-1,25),'P08':(7.3,10),'P09':(-1,6),'P10':(10.45,32.9),'P11':(55,5),'P12':(8.5,-3.4),'P13':(22,3.4),'P14':(-1,20),'P15':(5.1,24.9),'P16':(-1,2),'P17':(9,14),'P18':(-1,29),'P19':(12.5,-3.4)}
    for pid in ids:
        x,y=coords[pid];size=float(p.loc[pid,GROUPS[0]])*100*35
        core=types[pid]=='机制';color=C[0] if core else '#8799A5'
        ax.scatter(x,y,s=size,c=color,alpha=.70,edgecolors='white',linewidth=1.2,zorder=3)
        tx,ty=numberpos[pid]
        if math.hypot(tx-x,ty-y)>2:ax.plot([x,tx],[y,ty],color=GRAY,lw=.85,zorder=2)
        in_bubble=math.hypot(tx-x,ty-y)<1
        ax.text(tx,ty,str(int(pid[1:])),ha='center',va='center',fontsize=10.5,weight='bold',color='white' if in_bubble and size>250 else INK,zorder=4)
    # Compact key shows the target attention separately from automatic problem expressions.
    side=fig.add_axes([.69,.20,.285,.65]);side.axis('off');side.set_xlim(0,1);side.set_ylim(0,1)
    side.text(0,1.015,'编号与问题主题',fontsize=13,color=INK,weight='bold')
    side.text(.78,1.015,'固态锂硫',fontsize=11,color=C[0],ha='center',weight='bold')
    side.text(.97,1.015,'问题措辞',fontsize=10,color=MUTED,ha='right')
    # Rows align with ID order; percentages are fixed from the existing frequencies.
    for j,pid in enumerate(ids):
        y=.955-j*.046;core=types[pid]=='机制';col=C[0] if core else '#788C98'
        issue=freq[(freq['时段']=='2023-2026')&(freq['口径']=='校正主集')&(freq['模式']=='问题措辞')&(freq['体系']==GROUPS[0])&(freq['标签号']==pid)].iloc[0]
        side.text(0,y,f'{int(pid[1:]):02}',fontsize=10.5,color=col,weight='bold')
        side.text(.085,y,short[pid],fontsize=10.3,color=INK)
        side.text(.80,y,f'{p.loc[pid,GROUPS[0]]*100:.1f}%',fontsize=10.5,color=C[0],ha='right')
        side.text(.98,y,f'{issue["占比"]*100:.1f}%',fontsize=10.5,color=MUTED,ha='right')
    title(fig,'筛选主线：目标体系关心程度 × 两类来源的关注分布','横纵轴分别是两类来源中的提及率；气泡面积表示固态锂硫的提及率。位置保持原始数据，编号用引线避让。')
    handles=[Line2D([0],[0],marker='o',color='w',markerfacecolor=C[0],markersize=10,label='机制主题'),Line2D([0],[0],marker='o',color='w',markerfacecolor='#8799A5',markersize=10,label='工况/工程约束')]
    fig.legend(handles=handles,loc='lower left',bbox_to_anchor=(.075,.085),ncol=2,frameon=False,fontsize=11)
    sizeax=fig.add_axes([.70,.135,.25,.085]);sizeax.axis('off');sizeax.set_xlim(0,1);sizeax.set_ylim(0,1)
    sizeax.text(0,.9,'气泡面积：固态锂硫提及率',fontsize=10.5,color=MUTED,va='top')
    for x,pc in zip([.14,.47,.82],[10,25,50]):
        sizeax.scatter(x,.32,s=pc*35,c=C[0],alpha=.70,edgecolors='white',linewidth=1.2)
        sizeax.text(x,-.12,f'{pc}%',ha='center',va='top',fontsize=10,color=MUTED)
    fig.text(.035,.060,'虚线为5%阅读参考线，不是课题入选标准。右表“问题措辞”仍可能是背景或已改善对象，不能直接当作未解决问题。',fontsize=10.5,color=MUTED)
    fig.text(.035,.027,'该图帮助选择应比较哪类来源方法；不把三体系都高频设为必要条件，也不据图给材料、策略或研究主线打总分。',fontsize=10.5,color=MUTED)
    save(fig,'07_主线筛选来源气泡图')
    rows=[]
    for pid in ids:rows.append({'标签号':pid,'主题':labels[pid],'X液态锂硫提及率':float(p.loc[pid,GROUPS[1]]),'Y固态锂金属提及率':float(p.loc[pid,GROUPS[2]]),'面积对应固态锂硫提及率':float(p.loc[pid,GROUPS[0]])})
    pd.DataFrame(rows).to_csv(DEST/'主线筛选_气泡坐标.csv',index=False,encoding='utf-8-sig')

def summary_doc():
    selected,_=build_edges();mem=membership();reg=collections.defaultdict(list)
    for pid,m in mem.items():reg[m].append(pid)
    lines=['# 三体系综合关系图：读图与选题用途','',
    '沿用既有2023—2026年摘要统计：固态锂硫289篇、液态锂硫3,109篇、固态锂金属2,440篇。本轮只重构图形与比较方式，没有重跑文献抽取或改变问题标签。',
    '', '## 1. 一张重叠图：哪些体系较常关注同一个问题？','',
    '![三体系问题重叠图](05_三体系问题重叠图.png)','',
    '**按是否检出，19类主题中18类在三组均出现；只有“多硫化物溶解/穿梭”在本次固态锂金属子集中为0篇。** 这不证明该主题永远不会出现在固态锂金属相关论文中。',
    '', '因此主图按“组内提及率至少5%，且至少5篇”区分较常关注的区域。图中的独区只表示“仅该体系达到门槛”，不表示该问题为其独有；圆面积不代表论文数或主题数。', '',
    '|达到门槛的体系|主题|','|---|---|']
    for m in [(1,1,1),(1,1,0),(1,0,1),(0,1,1),(1,0,0),(0,1,0),(0,0,1),(0,0,0)]:lines.append('|'+fmtmask(m)+'|'+'；'.join(labels[x] for x in reg[m])+'|' if reg[m] else '|'+fmtmask(m)+'|无|')
    lines+=['','**门槛附近的主题尤其需要看原比例。** 例如副反应在液态锂硫为4.7%，室温/温度条件为5.1%；不能用一条5%线将它们解释为物理上的不存在或存在。1%、3%、5%、10%的结果见“主题重叠及阈值敏感性.csv”。',
    '', '## 2. 一张共享网络：共现关系在哪些体系重复出现？','',
    '![三体系共享网络](06_三体系共享共现网络.png)','',
    '每个机制主题只有一个节点。扇区颜色沿用三体系配色；节点总面积对应三组提及率的均值，扇区对应三组提及率的相对份额，避免大组文献数量压过小组。连线是同一体系内部的论文共现；同一对问题的多色线表示多个体系都达到显示门槛。',
    '', '显示规则统一为cosine ≥ 0.25，且共现篇数 ≥ max(5,该组文献数的1%)。为了让三组网络叠在一图后仍可阅读，较前版单体系图提高了cosine显示门槛，但原始计数没有改变。未达到门槛不表示没有共现。',
    '', f'本图有{len(selected)}对关系，其中{sum(sum(m)>=2 for m in selected.values())}对在两个及以上体系达门槛，{sum(sum(m)==3 for m in selected.values())}对在三体系均达门槛。典型关系如下：', '',
    '|共现关系|达到显示门槛的体系|','|---|---|',
    '|离子输运—反应/转化动力学|固态锂硫、液态锂硫|',
    '|电子输运—反应/转化动力学|固态锂硫、液态锂硫|',
    '|离子输运—界面接触|固态锂硫、固态锂金属|',
    '|界面接触—界面阻抗|固态锂硫、固态锂金属|',
    '|副反应/界面化学—电位稳定性|三体系|','',
    '**这些是共现关系的重叠，不是因果边。** 最后一对也存在词义邻近，不能因此称其为最有创新性的主线。网络布局只是共同的图形布局，不证明机制聚类。',
    '', '## 3. 一张来源气泡图：选定问题后，优先比较哪类文献？','',
    '![主线筛选来源图](07_主线筛选来源气泡图.png)','',
    '横轴为液态锂硫关注比例，纵轴为固态锂金属关注比例，气泡面积为固态锂硫关注比例。读图时先看目标体系的大气泡，再看它靠近哪类来源，最后回读摘要/全文判断具体限制与作用位置。右侧附目标体系的提及率与问题措辞比例，避免把常规性能报告误读为未解决问题。',
    '', '- 转化动力学：固态锂硫22.5%、液态锂硫47.2%、固态锂金属2.4%。适合优先比较硫反应调控方法；不要求固态锂金属也把“硫转化”列为热点。',
    '- 离子传输：固态锂硫47.8%、液态锂硫16.4%、固态锂金属64.6%。适合比较固态输运方法，但其中包含电导测量与改善结果，不能直接把最高词频定成核心瓶颈。',
    '- 接触：固态锂硫12.5%、液态锂硫2.6%、固态锂金属13.1%。适合比较固态接触处理方法，仍要核对发生在正极、负极还是电解质内部。',
    '', '对当前选题，图形支持继续比较“固态硫转化动力学受限”这条候选主线及其限制来源。它没有把某个材料、组合或双变量实验选出来。接触、输运、副反应可以是同一主问题的候选原因，也可能是独立备选问题，需要全文证据来取舍。',
    '', '## 使用建议与文件','',
    '汇报时先用重叠图讲三体系的关系，再用共享网络展示共同讨论的关系，最后用来源气泡图解释为什么选择某个问题去比较方法。三图分工不同，不必用复杂网络替代全部论证。',
    '', '已提供PNG、可编辑SVG、GraphML以及对应CSV。原统计的检索倾向、摘要缺失、自动分组、正负极位置混合和语义误判限制仍然适用；本轮没有完成独立的全库人工验证。',
    '', '图中“重叠”与“仅某体系达到门槛”均为本地语料、特定词表和显示门槛下的结果。']
    (DEST/'综合关系图_读图说明.md').write_text('\n'.join(lines),encoding='utf-8')
    manifest={'数据源':str(OUT),'主分析期':'2023-2026','分母':den,'主题门槛':{'提及率':.05,'最少篇数':5},'共现门槛':{'cosine':.25,'最少共现':'max(5, ceil(0.01*N))'},'输入SHA256':{f:hashlib.sha256((OUT/f).read_bytes()).hexdigest() for f in ['问题频率_跨体系与时段.csv','共现网络_全部边.csv']}}
    (DEST/'图形参数.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    # Check that the seven Venn regions and outside account for each theme exactly once.
    assert sum(len(v) for v in reg.values())==len(ids)==19
    assert int(((counts>0).sum(axis=1)==3).sum())==18
    assert len(selected)==21 and sum(sum(m)>=2 for m in selected.values())==11
    net=nx.read_graphml(DEST/'三体系共享网络.graphml');assert len(net)==12 and net.number_of_edges()==21
    pd.DataFrame([{'检查':'主题分区覆盖','结果':'19类各计一次'},{'检查':'至少1篇的检出重叠','结果':'18类三组检出，1类两组检出'},{'检查':'共享网络导出','结果':'12节点、21关系；11关系多组达门槛'},{'检查':'气泡坐标','结果':'直接使用原提及率，未对点位添加扰动'}]).to_csv(DEST/'综合图校验.csv',index=False,encoding='utf-8-sig')
    archive=OUT/'三体系综合关系图_图表与数据.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in DEST.iterdir():
            if f.is_file():z.write(f,f.relative_to(OUT))
        z.write(Path(__file__),'unified_figures.py')
    print('Saved 3 shared-canvas figures, source CSVs, GraphML, explanatory report and ZIP:',archive)

if __name__=='__main__':venn();network();bubble();summary_doc()
