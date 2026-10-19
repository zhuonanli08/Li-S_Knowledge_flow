"""Abstract-level problem mapping, not a causal/mechanistic or performance ranking."""
from pathlib import Path
import sys, re, json, math, itertools, collections, hashlib
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT/'_deps'))
import numpy as np
import pandas as pd
from prepare_corpus import norm

# label, issue label, type, mention regex, explicit limitation/problem regex.
# A problem expression may describe a background limitation or a solved target.
# It is NEVER interpreted as proof that the problem persists in that paper.
RULES=[
('P01','离子传输/电导','离子传输受限','机制',r'ionic conductiv\w*|ion(?:ic)? transport|ion(?:ic)? diffusion|li(?:thium)?[+ -]*(?:ion)?[ -]*(?:transport|diffusion|conductiv\w*)|ion migration|transference number',r'(?:low|poor|limited|insufficient|sluggish|slow|inferior)\s+(?:\w+[ -]){0,4}(?:ionic conductiv\w*|ion(?:ic)? transport|ion(?:ic)? diffusion|li(?:thium)?[+ -]*(?:ion)?[ -]*(?:transport|diffusion|conductiv\w*))|(?:ionic conductiv\w*|ion(?:ic)? transport|ion(?:ic)? diffusion)\s+(?:\w+[ -]){0,3}(?:limitation|bottleneck|barrier|hindered|limited)|ion[- ]transport limitation'),
('P02','电子传输/电导','电子传输受限','机制',r'electronic conductiv\w*|electrical conductiv\w*|electron(?:ic)? transport|electron(?:ic)? conduction|insulat\w* (?:nature|sulfur|sulphur|li2s)|(?:sulfur|sulphur|li2s)\W+(?:\w+\W+){0,2}insulat\w*',r'(?:low|poor|insufficient|limited|inferior)\s+(?:\w+[ -]){0,4}(?:electronic conductiv\w*|electrical conductiv\w*|electron(?:ic)? transport|electron(?:ic)? conduction)|insulat\w* (?:nature|sulfur|sulphur|li2s)|(?:sulfur|sulphur|li2s)\W+(?:\w+\W+){0,2}insulat\w*'),
('P03','反应/转化动力学','反应/转化动力学慢','机制',r'(?:reaction|redox|conversion|electrochemical|sulfur|sulphur) kinetics|(?:sulfur|sulphur|polysulfide\w*|polysulphide\w*) (?:redox|conversion)|solid[- ]solid (?:reaction|conversion)|(?:li2s|lithium sulfide) (?:oxidation|decomposition|nucleation)',r'(?:sluggish|slow|poor|limited|hindered|retarded)\s+(?:\w+[ -]){0,5}(?:kinetics|conversion|redox|reaction)|(?:kinetic|reaction|conversion|redox) (?:barrier|limitation|bottleneck)|(?:conversion|redox|reaction) kinetics\s+(?:\w+\s+){0,2}(?:slow|sluggish)|(?:li2s|lithium sulfide)\s+(?:\w+\s+){0,3}(?:activation barrier|decomposition barrier)'),
('P04','界面接触/润湿','接触不良/接触丧失','机制',r'interfacial contact|interface contact|solid[- ]solid contact|physical contact|contact loss|loss of contact|contact area|wetting|wettability|intimate contact|poor contact',r'poor\s+(?:\w+[ -]){0,4}contact|(?:insufficient|limited|inadequate|unstable|sluggish)\s+(?:\w+[ -]){0,3}contact|contact loss|loss of contact|contact (?:degradation|failure)|(?:poor|limited|insufficient)\s+(?:\w+\s+){0,2}wett(?:ing|ability)|non[- ]wetting'),
('P05','界面阻抗/界面传输','界面阻抗/传输障碍','机制',r'interfacial (?:resistance|impedance|transport)|interface (?:resistance|impedance)|charge[- ]transfer (?:resistance|impedance)|space[- ]charge',r'(?:high|large|huge|increased|excessive)\s+(?:\w+[ -]){0,3}(?:interfacial (?:resistance|impedance)|interface (?:resistance|impedance)|charge[- ]transfer (?:resistance|impedance))|(?:interfacial|interface) (?:resistance|impedance)\s+(?:\w+\s+){0,2}(?:increase|growth|high|large)|space[- ]charge (?:layer|barrier)'),
('P06','副反应/界面化学','副反应/化学不稳定','机制',r'side reaction|parasitic reaction|interfacial reaction|electrolyte decomposition|interfacial stability|chemical stability|chemical incompatib\w*|electrolyte degrad\w*|unstable interface|interfacial instability|interphase growth|lithium corrosion',r'side reaction|parasitic reaction|electrolyte decomposition|electrolyte degrad\w*|chemical incompatib\w*|unstable interface|interfacial instability|interphase growth|lithium corrosion|(?:poor|low|insufficient)\s+(?:\w+[ -]){0,2}(?:interfacial|chemical) stability'),
('P07','电位稳定性/窗口','电位窗口窄/不稳定','机制',r'electrochemical stability|electrochemical window|stability window|oxidative stability|reductive stability|oxidation stability|reduction stability',r'(?:narrow|limited|poor|low|insufficient)\s+(?:\w+[ -]){0,3}(?:electrochemical stability|electrochemical window|stability window|oxidative stability|reductive stability)|electrochemical instability'),
('P08','体积变化/应力','体积变化/应力问题','机制',r'volume (?:change|expansion|variation)|volumetric (?:change|expansion)|chemo[- ]mechanical|chemomechanical|mechanical stress|mechanical strain',r'volume (?:change|expansion|variation)|volumetric (?:change|expansion)|chemo[- ]mechanical|chemomechanical|mechanical stress|mechanical strain'),
('P09','裂纹/孔洞/结构失效','裂纹/孔洞/结构失效','机制',r'crack\w*|fracture\w*|void formation|interfacial void|pulveriz\w*|delamination|structural (?:degradation|failure|collapse)',r'crack\w*|fracture\w*|void formation|interfacial void|pulveriz\w*|delamination|structural (?:degradation|failure|collapse)'),
('P10','枝晶/不均匀沉积','枝晶/不均匀沉积','机制',r'dendrit\w*|uneven lithium|non[- ]uniform lithium|inhomogeneous lithium|uneven li deposition|dead lithium',r'dendrit\w*|uneven lithium|non[- ]uniform lithium|inhomogeneous lithium|uneven li deposition|dead lithium'),
('P11','多硫化物溶解/穿梭','多硫化物溶解/穿梭','机制',r'shuttl\w*|polysul(?:f|ph)ide\w* (?:dissolution|diffusion|migration)|(?:dissolution|migration) of (?:lithium )?polysul(?:f|ph)ide\w*',r'shuttl\w*|polysul(?:f|ph)ide\w* (?:dissolution|diffusion|migration)|(?:dissolution|migration) of (?:lithium )?polysul(?:f|ph)ide\w*'),
('P12','硫利用/转化程度','利用不足/转化不完全','机制',r'sul(?:f|ph)ur utilization|utilization of (?:the )?sul(?:f|ph)ur|active material utilization|incomplete conversion|incomplete reaction|low utilization|poor utilization|limited utilization|irreversible (?:sulfur|sulphur|li2s)',r'(?:low|poor|limited|insufficient)\s+(?:\w+[ -]){0,3}utilization|incomplete (?:conversion|reaction)|irreversible (?:sulfur|sulphur|li2s)'),
('P13','高载量/厚电极','高载量/厚电极约束','工况',r'(?:high|higher|practical)\s+(?:\w+[ -]){0,2}(?:sulfur|sulphur|mass|areal) loading|thick (?:cathode|electrode)|high[- ]loading|high sulfur content',r'(?:high|higher|practical)\s+(?:\w+[ -]){0,2}(?:sulfur|sulphur|mass|areal) loading|thick (?:cathode|electrode)|high[- ]loading|high sulfur content'),
('P14','压力/力学强度','压力依赖/力学不足','工况',r'stack pressure|stacking pressure|external pressure|operating pressure|low[- ]pressure|high[- ]pressure|mechanical strength|mechanical robustness|brittleness',r'(?:high|large|excessive)\s+(?:stack|stacking|external|operating) pressure|(?:poor|low|weak|insufficient)\s+(?:\w+[ -]){0,2}mechanical (?:strength|robustness)|brittleness|pressure[- ]dependent|pressure dependence'),
('P15','室温/温度条件','低温/室温运行受限','工况',r'room[- ]temperature|low[- ]temperature|elevated temperature|high[- ]temperature|temperature depend\w*',r'(?:poor|low|limited|sluggish)\s+(?:\w+[ -]){0,4}(?:room[- ]temperature|low[- ]temperature)|(?:require\w*|need\w*)\s+(?:\w+[ -]){0,2}(?:elevated|high) temperature'),
('P16','空气/水稳定性','空气/水敏感性','机制',r'air stability|air[- ]stable|moisture stability|moisture[- ]sensitive|air[- ]sensitive|moisture sensitivity|air sensitivity|hydrogen sulfide|h2s (?:release|generation)',r'moisture[- ]sensitive|air[- ]sensitive|moisture sensitivity|air sensitivity|(?:poor|low) air stability|hydrogen sulfide|h2s (?:release|generation)'),
('P17','加工/规模化','加工/规模化约束','工程',r'scalab\w*|scale[- ]up|mass production|manufactur\w*|processability|processing challenge|fabrication challenge',r'(?:poor|limited|low) processability|processing challenge|fabrication challenge|difficult\w*\s+(?:\w+\s+){0,2}(?:manufactur\w*|scal\w*)'),
('P18','热安全/易燃','易燃/热失控','工程',r'flammab\w*|thermal runaway|thermal stability|fire hazard|safety concern|safety issue',r'flammab\w*|thermal runaway|fire hazard|safety concern|safety issue'),
('P19','少电解液/非活性占比','少电解液/非活性占比','工况',r'lean electrolyte|electrolyte[- /]to[- /]sulfur|electrolyte/sulfur|inactive (?:mass|weight|component|material)|electrolyte thickness',r'lean electrolyte|electrolyte[- /]to[- /]sulfur|electrolyte/sulfur|inactive (?:mass|weight|component|material)|electrolyte thickness'),
]
GROUPS=['固态锂硫','液态锂硫','固态锂金属']
# Corrections from evidence-sentence audit; applied identically to every group.
RULES=[list(r) for r in RULES]
RULES[0][4]+=r'|ionic percolation|ion[- ]conducting pathway'
RULES[0][5]+=r'|(?:poor|limited|insufficient) ionic percolation|(?:low|poor|limited) ion conductivity'
RULES[1][4]+=r'|(?:low|poor|insufficient) conductiv\w* of (?:the )?(?:sulfur|sulphur|li2s)|(?:sulfur|sulphur|li2s).{0,35}(?:electronically insulating)'
RULES[1][5]+=r'|(?:low|poor|insufficient) conductiv\w* of (?:the )?(?:sulfur|sulphur|li2s)|(?:sulfur|sulphur|li2s).{0,35}(?:electronically insulating)'
RULES[2][5]=r'(?:sluggish|slow|retarded)\s+(?:(?:solid[- ]solid|solid[- ]state|sulfur|sulphur|redox|reaction|conversion|electrochemical|cathode|activation|and|intrinsic)\s+){0,5}(?:kinetics|conversion|redox|reaction)|(?:poor|limited)\s+(?:reaction|redox|conversion|electrochemical) kinetics|(?:kinetic|reaction|conversion|redox) (?:barrier|limitation|bottleneck)|(?:conversion|redox|reaction) kinetics\s+(?:is |are |remain )?(?:slow|sluggish)|(?:li2s|lithium sulfide)\s+(?:\w+\s+){0,3}(?:activation barrier|decomposition barrier)'
RULES[2][4]+=r'|charge[- ]transfer kinetics|electrode kinetics|(?:plating|stripping|deposition)(?:[/ -](?:plating|stripping|deposition))? kinetics|interfacial kinetics'
RULES[2][5]+=r'|(?:sluggish|slow|poor|limited)\s+(?:charge[- ]transfer|interfacial|plating|stripping|deposition)(?:[/ -](?:plating|stripping|deposition))? kinetics'
RULES[4][5]=r'(?:high|large|huge|increased|excessive)\s+(?:\w+[ -]){0,3}(?:interfacial (?:resistance|impedance)|interface (?:resistance|impedance)|charge[- ]transfer (?:resistance|impedance))|(?:interfacial|interface) (?:resistance|impedance) (?:is |are |remains? )?(?:high|large|increases?\b)|space[- ]charge (?:layer|barrier)'
RULES[18][4]+=r'|\be/s ratio'
RULES[18][5]+=r'|\be/s ratio'
RULES[11][1]='活性物利用/转化程度'
RULES[11][4]+=r'|cathode utilization|utilization of (?:the )?(?:cathode|active material)'
RULES[17][5]=r'(?<!non)(?<!non-)(?<!non )flammab\w*|thermal runaway|fire hazard|safety concern|safety issue'

def valid_hit(match,j,s,r,issue=False):
    if not match:return False
    following=s[match.end():match.end()+65]
    if j==0 and issue and re.match(r'\s+(?:energy\s+)?barrier',following):return False
    if j==1 and issue and match.group().startswith('low'):
        # Low electron conduction can be DESIRABLE in an electrolyte/interphase.
        if not re.search(r'poor|insufficient|hinder|limit|restrict|bottleneck|challenge|sulfur|sulphur|li2s|cathode',s):return False
    if j==8 and match.group().startswith('fractur') and re.match(r'\s+of\s+.{0,35}bonds?\b',following):return False
    if j==10:
        # "Shuttle" can mean benign anion/Li-ion transport outside Li-S.
        if not re.search(r'polysul(?:f|ph)ide|sulfur|sulphur|li[- ]s\b',norm(r['abstract']+' '+r['title'])):return False
        if re.search(r'as a shuttle|shuttle of anions|shuttle to transfer',s):return False
    if j==6 and issue and match.group()=='electrochemical instability':
        if not re.search(r'electrolyte|interfac|potential|voltage|window|anode',s):return False
    return True

def find_valid(pat,j,s,r,issue=False):
    return next((m for m in pat.finditer(s) if valid_hit(m,j,s,r,issue)),None)
def wilson(k,n):
    if not n:return (0.,0.)
    p=k/n; z=1.96; c=(p+z*z/(2*n))/(1+z*z/n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return c-h,c+h

def run():
    data=json.loads((OUT/'corpus.json').read_text(encoding='utf-8'))
    n=len(data); k=len(RULES); M=np.zeros((n,k),dtype=np.uint8); B=M.copy(); evidence=[]
    pats=[(re.compile(r[4]),re.compile(r[5])) for r in RULES]
    for i,r in enumerate(data):
        # Abstract only: title is used for grouping, not for term frequencies.
        txt=norm(r['abstract'])
        sentences=re.split(r'(?<=[.!?])\s+(?=[a-z])',txt)
        for j,(pm,pb) in enumerate(pats):
            hits=[(s,find_valid(pm,j,s,r),find_valid(pb,j,s,r,True)) for s in sentences]
            mh=[h for h in hits if h[1] or h[2]]; bh=[h for h in hits if h[2]]
            if mh:M[i,j]=1
            if bh:B[i,j]=1
            if mh:
                best=(bh or mh)[0]; s,mm,bb=best
                evidence.append({'体系':r['group'],'编号':r['id'],'年份':r['year'],'DOI':r['doi'],'标题':r['title'],'标签号':RULES[j][0],'主题':RULES[j][1],'问题表述':RULES[j][2],'标签类型':RULES[j][3],'有瓶颈或问题措辞':bool(bh),'命中短语':(bb or mm).group(),'摘要证据句_规范化':s,'严格分组':r['strict']})
    ev=pd.DataFrame(evidence);ev.to_csv(OUT/'逐篇主题与证据.csv',index=False,encoding='utf-8-sig')
    assert np.all(B<=M), 'Problem-expression matrix must be a subset of mention matrix'
    pd.DataFrame(RULES,columns=['标签号','主题','问题表述','类型','一般提及正则','问题措辞正则']).to_csv(OUT/'词表与匹配规则.csv',index=False,encoding='utf-8-sig')
    years=np.array([r['year'] for r in data]); gs=np.array([r['group'] for r in data]); strict=np.array([r['strict'] for r in data]);focus=np.array([r['focus'] for r in data])
    stats=[];edges=[]
    for g in GROUPS:
      for period,ymask in [('2010-2026',years>=2010),('2010-2022',years<2023),('2023-2026',years>=2023)]:
       for scope,smask in [('校正主集',np.ones(n,dtype=bool)),('严格子集',strict),('题名聚焦子集',focus)]:
        ix=(gs==g)&ymask&smask; den=int(ix.sum())
        for mode,X in [('一般提及',M),('问题措辞',B)]:
         freq=X[ix].sum(axis=0)
         for j,r in enumerate(RULES):
            count=int(freq[j]);lo,hi=wilson(count,den)
            stats.append({'体系':g,'时段':period,'口径':scope,'模式':mode,'标签号':r[0],'主题':r[1],'问题表述':r[2],'类型':r[3],'篇数':count,'分母':den,'占比':count/den if den else None,'Wilson下限':lo,'Wilson上限':hi})
         if scope=='校正主集':
            co=X[ix].astype(np.int64).T@X[ix].astype(np.int64)
            for a,b in itertools.combinations(range(k),2):
                c=int(co[a,b]); na=int(freq[a]);nb=int(freq[b])
                edges.append({'体系':g,'时段':period,'模式':mode,'A':RULES[a][0],'B':RULES[b][0],'主题A':RULES[a][1],'主题B':RULES[b][1],'共现篇数':c,'分母':den,'共现比例':c/den if den else 0,'A篇数':na,'B篇数':nb,'cosine':c/math.sqrt(na*nb) if na*nb else 0,'lift':c*den/(na*nb) if na*nb else 0,'Jaccard':c/(na+nb-c) if na+nb-c else 0})
    st=pd.DataFrame(stats);ed=pd.DataFrame(edges)
    st.to_csv(OUT/'问题频率_跨体系与时段.csv',index=False,encoding='utf-8-sig');ed.to_csv(OUT/'共现网络_全部边.csv',index=False,encoding='utf-8-sig')
    # Deterministic stratified audit sample, including hits and missed abstracts.
    sample=[]
    for g in GROUPS:
        ge=ev[(ev['体系']==g)&(ev['年份']>=2023)]
        for j,r in enumerate(RULES[:12]):
            eligible=ge[(ge['标签号']==r[0])&ge['有瓶颈或问题措辞']].copy()
            eligible['sortkey']=eligible['编号'].map(lambda s:hashlib.sha256((s+r[0]).encode()).hexdigest())
            sample.extend(eligible.sort_values('sortkey').head(2).drop(columns='sortkey').to_dict('records'))
    pd.DataFrame(sample).to_json(OUT/'audit_sample.json',orient='records',force_ascii=False)
    np.savez_compressed(OUT/'matrices.npz',M=M,B=B,years=years,strict=strict,focus=focus,groups=gs)
    display=st[(st['时段']=='2023-2026')&(st['口径']=='校正主集')]
    for g in GROUPS:
        print('\n'+g)
        print(display[(display['体系']==g)&(display['模式']=='问题措辞')][['问题表述','篇数','分母','占比']].sort_values('篇数',ascending=False).to_string(index=False))
    print('\nRECENT SOLID NETWORK')
    print(ed[(ed['体系']=='固态锂硫')&(ed['时段']=='2023-2026')&(ed['模式']=='问题措辞')&(ed['共现篇数']>=5)].sort_values('cosine',ascending=False).head(15).to_string(index=False))
if __name__=='__main__':run()
