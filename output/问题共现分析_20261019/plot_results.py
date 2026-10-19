from pathlib import Path
import sys, json, math
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT/'_deps'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
import networkx as nx
from wordcloud import WordCloud
from analyze import RULES,GROUPS
FONT='C:/Windows/Fonts/msyh.ttc'
font_manager.fontManager.addfont(FONT)
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'svg.fonttype':'none','font.size':11,'figure.facecolor':'white','axes.spines.top':False,'axes.spines.right':False})
INK='#193348';GRAY='#526777';COLORS=['#087F8C','#C56B27','#6954A3']
st=pd.read_csv(OUT/'问题频率_跨体系与时段.csv');ed=pd.read_csv(OUT/'共现网络_全部边.csv')
recent=st[(st['时段']=='2023-2026')&(st['口径']=='校正主集')]
den={g:int(recent[recent['体系']==g]['分母'].iloc[0]) for g in GROUPS}
labs={r[0]:r[1] for r in RULES}
FIG=OUT/'图表';FIG.mkdir(exist_ok=True)
def save(fig,name):
    fig.savefig(FIG/(name+'.png'),dpi=200,bbox_inches='tight',facecolor='white')
    fig.savefig(FIG/(name+'.svg'),bbox_inches='tight',facecolor='white')
    plt.close(fig)
def headline(fig,title,sub):
    fig.suptitle(title,x=.03,y=.99,ha='left',color=INK,fontsize=20,fontweight='bold')
    fig.text(.03,.99-.60/fig.get_figheight(),sub,ha='left',color=GRAY,fontsize=11)

def heatmap():
    ids=recent[(recent['体系']==GROUPS[0])&(recent['模式']=='一般提及')].sort_values('占比',ascending=False)['标签号'].tolist()
    fig,axes=plt.subplots(1,2,figsize=(16,11),gridspec_kw={'width_ratios':[1,1]})
    fig.subplots_adjust(left=.20,right=.97,top=.85,bottom=.12,wspace=.17)
    cmap=LinearSegmentedColormap.from_list('teal',['#F3F7F9','#B4DADE','#388F9B','#075164'])
    for ai,mode in enumerate(['一般提及','问题措辞']):
        ax=axes[ai];arr=np.array([[float(recent[(recent['体系']==g)&(recent['标签号']==p)&(recent['模式']==mode)]['占比'].iloc[0])*100 for g in GROUPS] for p in ids])
        ax.imshow(arr,cmap=cmap,vmin=0,vmax=75,aspect='auto')
        ax.set_xticks(range(3),[g+'\nn='+str(den[g]) for g in GROUPS]);ax.xaxis.tick_top();ax.tick_params(length=0)
        ax.set_yticks(range(len(ids)),[labs[p]+(' †' if RULES[int(p[1:])-1][3]!='机制' else '') for p in ids] if ai==0 else ['']*len(ids))
        ax.set_title('A  主题提及率' if ai==0 else 'B  检出问题或约束措辞的比例',fontsize=14,pad=44,color=INK)
        for row,p in enumerate(ids):
            for col,g in enumerate(GROUPS):
                rr=recent[(recent['体系']==g)&(recent['标签号']==p)&(recent['模式']==mode)].iloc[0]
                ax.text(col,row,f'{rr["占比"]*100:.1f}%  ({rr["篇数"]})',ha='center',va='center',fontsize=10,color='white' if arr[row,col]>42 else INK)
        for spine in ax.spines.values():spine.set_visible(False)
    headline(fig,'三体系关注什么问题？','2023—2026年本地摘要；同一主题每篇只计一次。括号为篇数，色深为占比，两图统一色阶。')
    fig.text(.03,.066,'A 包括背景、方法和结果中的提及；B 检出慢、低、不良等措辞或枝晶、穿梭等问题名词。B仍可能是背景问题或已改善对象。',fontsize=10,color=GRAY)
    fig.text(.03,.038,'† 工况或工程约束，单独标识。两图均不表示未解决问题的比例；分组和摘要覆盖限制见报告。',fontsize=10,color=GRAY)
    save(fig,'01_三体系问题热图')

def clouds():
    fig,axes=plt.subplots(1,3,figsize=(18,7.3));fig.subplots_adjust(left=.025,right=.98,top=.82,bottom=.12,wspace=.05)
    for j,(g,ax) in enumerate(zip(GROUPS,axes)):
        b=recent[(recent['体系']==g)&(recent['模式']=='一般提及')]
        freqs={r['主题']:r['占比'] for _,r in b.iterrows() if r['篇数']>0}
        wc=WordCloud(font_path=FONT,width=1200,height=1000,background_color='white',relative_scaling=.5,max_font_size=140,min_font_size=12,prefer_horizontal=1,random_state=41,collocations=False,margin=9,color_func=lambda *args,**kwargs:COLORS[j]).generate_from_frequencies(freqs)
        ax.imshow(wc,interpolation='bilinear');ax.axis('off');ax.set_title(f'{g}  ·  n={den[g]:,}',fontsize=17,color=COLORS[j],pad=18)
    headline(fig,'问题与约束主题词图','合并同义表述后的19类主题；数据来自摘要匹配，不使用材料名称代替问题。')
    fig.text(.03,.055,'每幅图内字号按该组提及比例排列；不同图各自缩放，跨体系数值比较请看热图。英文开放短语及完整映射已另存。',fontsize=11,color=GRAY)
    save(fig,'02_三体系问题词图')

def networks():
    ids=[r[0] for r in RULES[:12]]
    # Fixed circular positions avoid suggesting a causal order or learned cluster.
    pos={p:np.array([math.cos(math.pi/2-2*math.pi*i/len(ids)),math.sin(math.pi/2-2*math.pi*i/len(ids))]) for i,p in enumerate(ids)}
    label_short=['离子传输\n电导','电子传输\n电导','反应/转化\n动力学','界面接触\n润湿','界面阻抗\n传输','副反应\n界面化学','电位稳定性\n窗口','体积变化\n应力','裂纹/孔洞\n结构失效','枝晶\n不均匀沉积','多硫化物\n溶解/穿梭','活性物利用\n转化程度']
    fig,axes=plt.subplots(1,3,figsize=(19,8));fig.subplots_adjust(left=.01,right=.99,top=.83,bottom=.19,wspace=.02)
    plotted=[]
    for gi,(g,ax) in enumerate(zip(GROUPS,axes)):
        b=recent[(recent['体系']==g)&(recent['模式']=='一般提及')].set_index('标签号')
        threshold=max(5,math.ceil(.01*den[g]))
        e=ed[(ed['体系']==g)&(ed['时段']=='2023-2026')&(ed['模式']=='一般提及')&ed['A'].isin(ids)&ed['B'].isin(ids)&(ed['共现篇数']>=threshold)&(ed['cosine']>=.12)].sort_values('cosine',ascending=False).head(20)
        G=nx.Graph();G.add_nodes_from(ids)
        for _,r in e.iterrows():G.add_edge(r['A'],r['B'],weight=r['cosine']);plotted.append(r.to_dict())
        nx.draw_networkx_edges(G,pos,ax=ax,width=[8*G[u][v]['weight'] for u,v in G.edges()],edge_color=COLORS[gi],alpha=.32)
        nx.draw_networkx_nodes(G,pos,ax=ax,node_size=[2200*float(b.loc[p,'占比']) for p in ids],node_color=COLORS[gi],edgecolors='white',linewidths=1.5)
        for i,p in enumerate(ids):
            x,y=pos[p]*1.29;ax.text(x,y,label_short[i],ha='center',va='center',fontsize=10.5,color=INK)
        ax.set_xlim(-1.72,1.72);ax.set_ylim(-1.6,1.6);ax.axis('off');ax.set_aspect('equal')
        ax.set_title(f'{g}  ·  n={den[g]:,}\n共现至少{threshold}篇；展示{len(e)}条边',fontsize=14,color=COLORS[gi],pad=12)
    headline(fig,'哪些问题在同一篇论文中共同出现？','近期摘要的主题共现网络。三组节点位置固定，便于比较；网络位置不代表机制或因果。')
    fig.text(.03,.115,'节点面积 ∝ 提及比例；连线粗细 ∝ cosine = 共现篇数 / √(A篇数×B篇数)。仅画12类机制主题。',fontsize=11,color=GRAY)
    fig.text(.03,.073,'保留共现≥max(5篇,1%组内文献)、cosine≥0.12的前20条边；阈值之外的全部边保存在数据表。',fontsize=11,color=GRAY)
    fig.text(.03,.032,'共现说明共同讨论，不说明作用链条、策略有效性或知识迁移。不同体系相同标签，也可能处于不同电极位置。',fontsize=11,color=GRAY)
    pd.DataFrame(plotted).to_csv(OUT/'共现网络_绘图边.csv',index=False,encoding='utf-8-sig')
    save(fig,'03_三体系共现网络')

def trends():
    ids=['P01','P03','P06','P08','P04','P12','P10','P11']
    fig,axes=plt.subplots(1,3,figsize=(17,7.8));fig.subplots_adjust(left=.15,right=.97,top=.82,bottom=.19,wspace=.30)
    for gi,(g,ax) in enumerate(zip(GROUPS,axes)):
        for i,p in enumerate(ids):
            pts=[]
            for period,c,marker in [('2010-2022','#A8B7BF','o'),('2023-2026',COLORS[gi],'o')]:
                rr=st[(st['体系']==g)&(st['标签号']==p)&(st['时段']==period)&(st['口径']=='校正主集')&(st['模式']=='一般提及')].iloc[0]
                x=rr['占比']*100;pts.append(x)
                ax.scatter(x,i,s=70,color=c,zorder=3)
            ax.plot(pts,[i,i],color='#B9C6CC',linewidth=2,zorder=1)
            ax.text(pts[1]+1.4,i,f'{pts[1]:.1f}',fontsize=9.5,va='center',color=COLORS[gi])
        ax.set_yticks(range(len(ids)),[labs[p] for p in ids] if gi==0 else ['']*len(ids));ax.invert_yaxis();ax.set_xlim(0,85);ax.set_xlabel('提及比例（%）');ax.grid(axis='x',alpha=.15)
        ax.set_title(g,fontsize=16,color=COLORS[gi]);ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0)
    headline(fig,'近期关注结构与早期有何不同？','按各时段内部比例比较，避免文献数量增长直接抬高词频；同一套词表、同一筛选规则。')
    fig.legend(handles=[Line2D([0],[0],marker='o',color='#A8B7BF',linestyle='None',label='2010—2022'),Line2D([0],[0],marker='o',color=COLORS[0],linestyle='None',label='2023—2026（各组彩色）')],loc='lower left',bbox_to_anchor=(.13,.08),frameon=False,ncol=2)
    fig.text(.03,.032,'这是本地语料的关注变化，受检索、摘要缺失和分组影响；2026年不完整，不据此推断整个领域的因果或年度增长率。',fontsize=10,color=GRAY)
    save(fig,'04_问题关注随时段变化')

if __name__=='__main__':
    heatmap();clouds();networks();trends()
    print('Saved 4 PNG and 4 SVG figures to',FIG)
