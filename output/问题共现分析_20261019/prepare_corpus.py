"""Reproducible corpus selection. Original records are never changed."""
from pathlib import Path
import pandas as pd
import re, json, unicodedata, hashlib

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent.parent
SRC=ROOT/'output/dataset_v2/论文表.csv'
def norm(s):
    s=unicodedata.normalize('NFKC',str(s)).lower()
    s=re.sub('[‐‑‒–—−]','-',s)
    s=re.sub(r'\bli\s*2\s*s\b','li2s',s)
    s=re.sub(r'\bs\s*8\b','s8',s)
    return re.sub(r'\s+',' ',s).strip()
def rx(p,s): return bool(re.search(p,s,re.I))

def run():
    d=pd.read_csv(SRC,dtype=str).fillna('')
    d['原分组']=d['分组']
    d['核查依据']='原库规则分组，未逐篇全文核验'
    v=ROOT/'output/方案D_试点'
    scen=pd.read_csv(v/'敏感性情景清单.csv',dtype=str).fillna('')
    for _,r in scen.iterrows():
        new=r['情景 B（严格全固态边界）']
        if new:
            mask=d['编号'].eq(r['论文号']);d.loc[mask,'分组']=new
            d.loc[mask,'核查依据']='已有敏感性情景B：'+new
    # Existing paper-level reviews take precedence over inherited auto labels.
    rev={}
    b=pd.read_excel(v/'词表试点_批1.xlsx',sheet_name='论文核查').fillna('')
    for _,r in b.iterrows():
        grp=r['建议归属']
        if grp.startswith('非硫固态'): grp='固态锂电池'
        elif grp.startswith('液态锂硫'): grp='液态锂硫'
        elif grp!='固态锂硫': grp='边界/其他'
        rev[r['论文号']]={'group':grp,'type':r['文献类型'],'state':r['液相状态'],'source':'词表试点论文核查'}
    b=pd.read_excel(v/'组别核查_复核表.xlsx',sheet_name='组别核查_60篇').fillna('')
    for _,r in b.iterrows():
        grp=r['方案D 应用归属']
        if grp.startswith('固态锂硫'): grp='固态锂硫'
        elif grp=='液态锂硫': grp='液态锂硫'
        else: grp='边界/其他'
        rev[r['论文号']]={'group':grp,'type':r['文献类型'],'state':r['液相状态'],'source':'组别核查60篇'}
    rows=[]; seen_doi=set(); seen_title=set()
    solid_pat=r'(?:all[- ]solid[- ]state|solid[- ]state|solid polymer|solid electrolyte|solid-state electrolyte)'
    limetal=r'lithium[- ]metal|li[- ]metal|metallic lithium|lithium metal anode|lithium anode|anode[- ]free|lithium plating|lithium stripping'
    ssli=r'(?:all[- ]solid[- ]state|solid[- ]state)(?:\s+\w+){0,3}\s+(?:lithium[- ](?:sulfur|sulphur)|li[- ]s)\b|(?:lithium[- ](?:sulfur|sulphur)|li[- ]s)(?:\s+\w+){0,3}\s+(?:all[- ]solid[- ]state|solid[- ]state)\b'
    review_pat=r'\b(?:in this review|this review|the review|we review|we critically review|review article|review paper|mini-review|this perspective|this progress report|this paper reviews|this article reviews|this paper summarizes|this article summarizes|this work reviews|this work summarizes|are reviewed|is reviewed|comprehensively reviewed|systematically reviewed|comprehensive review|comprehensive overview|this account|conspectus)\b'
    review_title=r'\breview\b|\bperspective\b|\bperspectives\b|\bprospects\b|\bprogress\b|\brecent advances\b|\badvances in\b|\bcurrent status\b|\bchallenges and\b|\bapplications and challenges\b'
    # Supplemental exclusions, inspected directly in the saved abstract in this run.
    exclusions=json.loads((OUT/'manual_exclusions.json').read_text(encoding='utf-8')) if (OUT/'manual_exclusions.json').exists() else {}
    for _,r in d.iterrows():
        a=r['摘要'].strip(); t=norm(r['标题']); txt=t+' '+norm(a)
        rr=rev.get(r['编号']); g=r['分组']; state='未逐篇核实'; typ=r['文献类型']
        if rr:
            g=rr['group'];state=rr['state'];typ=rr['type'];r['核查依据']=rr['source']+'；'+state
        reasons=[]
        if r['来源']!='检索': reasons.append('仅补池')
        if not a: reasons.append('无摘要')
        if (r['文献类型']!='article' and not (rr and ('原创' in typ or typ in ['计算','方法']))) or '综述' in typ or '会议' in typ or '学位' in typ or '封面' in typ or rx(review_pat,txt) or rx(review_title,t): reasons.append('综述/非研究记录')
        if r['编号'] in exclusions: reasons.append('本轮摘要核查：'+exclusions[r['编号']])
        try: year=int(float(r['年份']))
        except: year=0
        if not 2010<=year<=2026: reasons.append('不在2010-2026范围')
        grp=''
        if g=='固态锂硫': grp='固态锂硫'
        elif g=='液态锂硫': grp='液态锂硫'
        elif g=='固态锂电池' and rx(limetal,txt) and rx(solid_pat,txt): grp='固态锂金属'
        if not grp: reasons.append('不属三组或锂金属证据不足')
        if grp.startswith('固态') and rr and ('含液' in state or '待核实' in state or state.startswith('液态')): reasons.append('已知含液/状态待核实')
        boundary=rx(r'quasi[- ]solid|semi[- ]solid|gel polymer electrolyte|gel electrolyte|ionogel',t)
        if grp.startswith('固态') and boundary: reasons.append('标题明确准固态/凝胶')
        if grp=='固态锂硫' and rx(r'\bfes\s*2\b|\bfe\s*s2\b',t): reasons.append('FeS2正极边界单列')
        if grp=='固态锂金属' and rx(r'lithium[- ]sul(?:f|ph)ur|li[- ]s\b|sul(?:f|ph)ur cathode',t): reasons.append('锂硫标题避免组间重复')
        doi=norm(r['DOI']).replace('https://doi.org/',''); titlekey=re.sub(r'\W','',t)
        if not reasons:
            if (doi and doi in seen_doi) or (titlekey and titlekey in seen_title): reasons.append('重复DOI/标题')
            else:
                if doi: seen_doi.add(doi)
                if titlekey: seen_title.add(titlekey)
        strict=False
        if grp=='固态锂硫': strict=(bool(rr and state=='全固态') or rx(ssli,txt))
        elif grp=='液态锂硫': strict=not rx(r'solid[- ]state|quasi[- ]solid|semi[- ]solid|gel electrolyte',t)
        elif grp=='固态锂金属':
            strict=rx(limetal,t) and rx(solid_pat,txt) or rx(solid_pat,t) and rx(limetal,t)
            # Additional exact compound in abstract; no scattered background-only matches.
            strict=strict or rx(r'(?:all[- ]solid[- ]state|solid[- ]state)(?:\s+\w+){0,2}\s+(?:lithium[- ]metal|li[- ]metal)',norm(a))
        focus=bool(strict and rx(r'lithium[- ]sul(?:f|ph)ur|li[- ]s\b|\bli2s\b|sulfur|sulphur|sulfurized|lithium sulfide',t)) if grp=='固态锂硫' else bool(strict)
        rows.append({'id':r['编号'],'doi':r['DOI'],'year':year,'title':r['标题'],'abstract':a,'original_group':r['原分组'],'corrected_group':g,'group':grp,'source':r['来源'],'review_basis':r['核查依据'],'electrolyte':r['电解质类型'],'cathode_route':r['正极路线'],'included':not reasons,'strict':bool(strict),'focus':focus,'exclusion':';'.join(reasons),'known_state':state})
    audit=pd.DataFrame(rows); audit.to_csv(OUT/'语料纳入审计.csv',index=False,encoding='utf-8-sig')
    c=audit[audit.included].copy(); c.to_json(OUT/'corpus.json',orient='records',force_ascii=False)
    summary={'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'raw_records':len(d),'included':len(c),'groups':{}}
    for g,b in c.groupby('group'):
        summary['groups'][g]={'all':len(b),'recent':int((b.year>=2023).sum()),'strict':int(b.strict.sum()),'strict_recent':int((b.strict & (b.year>=2023)).sum())}
    (OUT/'corpus_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':run()
