"""③a 证据汇总：每个方法类别在三体系的篇数、前提线索、代表原句；另找"哪条原因是主因"的诊断句。
只读 ../方法清单_硫转化动力学_20261019/_inventory.json 和问题共现分析的 corpus.json，不改它们。
"""
import json, re, sys, collections
from pathlib import Path

OUT = Path(__file__).resolve().parent
INV = OUT.parent / '方法清单_硫转化动力学_20261019'
sys.path.insert(0, str(INV))
from common import norm, own_sentences, load_corpus, sentences
from build_inventory import VOCAB, BATTERY_NAME

sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open(INV / '_inventory.json', encoding='utf-8'))
rows = d['rows']
corpus = {r['id']: r for r in load_corpus()}
full = {k: norm(v['title'] + ' ' + v['abstract']) for k, v in corpus.items()}

SULFIDE = re.compile(r'li6ps5|argyrodite|li3ps4|\blps\b|li7p3s11|lgps|li10gep2s12|thiophosphate|sulfide (?:solid )?electrolyte|sulfide-based|li2s-p2s5|\blpscl\b|\blpsc\b|glass(?:-ceramic)? electrolyte')
POLYMER = re.compile(r'\bpeo\b|poly ?\(ethylene oxide\)|polyethylene oxide|polymer electrolyte|\bspes?\b|\bcpes?\b|pvdf|\bgel\b|in[- ]situ polymeri')
OXHAL = re.compile(r'llzt?o|garnet|latp|lagp|nasicon|halide|li3incl6|li3ycl6|li3ycl')


def etype(pid):
    t = full[pid]
    s, p = bool(SULFIDE.search(t)), bool(POLYMER.search(t))
    if s and p: return '硫化物+聚合物'
    if s: return '硫化物'
    if p: return '聚合物'
    if OXHAL.search(t): return '氧化物/卤化物'
    return '未写明'


PRE = {
    '液态·依赖溶解多硫化物（吸附/锚定/穿梭）': re.compile(r'dissolv|soluble|shuttl|adsorb|adsorption|anchor\w*|trap\w*|immobili[sz]|chemisorption|polysulfide diffusion|diffusion of (?:lithium )?polysulfides?'),
    '液态·依赖液相浸润': re.compile(r'wetting|wettab|infiltrat|electrolyte uptake|electrolyte penetration|e/s ratio|lean electrolyte'),
    '液态·讲固相步骤（Li2S 成核/分解等）': re.compile(r'li2s (?:nucleation|deposition|precipitation|decomposition|oxidation|activation|dissociation|growth)|li2s2|solid[- ]solid|bidirectional'),
    '固态锂金属·针对负极': re.compile(r'\banodes?\b|li(?:thium)?[- ]metal anode|dendrit\w*|plating|stripping|\bsei\b'),
    '固态锂金属·针对高电压正极（抗氧化）': re.compile(r'high[- ]voltage|\b4\.\d ?v\b|\bncm|\bnmc|lini|licoo2|\blco\b|oxidation stability|oxidative stability|anti-oxidation'),
    '固态锂金属·含液或准固态成分': re.compile(r'ionic liquid|plastici[sz]|in[- ]situ polymeri|\bgel\b|succinonitrile|deep eutectic|quasi[- ]solid'),
    '固态锂金属·聚合物体系': POLYMER,
}
SRC_SCOPES = {'液态锂硫': [k for k in PRE if k.startswith('液态')], '固态锂金属': [k for k in PRE if k.startswith('固态锂金属')]}


def pick(rs, k=3):
    rs = sorted(rs, key=lambda r: (r['证据来源'] == '做法句', r['年份']), reverse=True)
    out, seen = [], set()
    for r in rs:
        if r['编号'] in seen: continue
        seen.add(r['编号'])
        out.append({'编号': r['编号'], '年份': r['年份'], 'DOI': r['DOI'], '电解质': etype(r['编号']) if r['范围'].startswith('固态锂硫') else '',
                    '原句': r['原句（规范化）'], '命中': r['命中短语'], '组分': r['改的组分']})
        if len(out) == k: break
    return out


report = {}
for code, cause, name, _ in VOCAB:
    if code == 'X01': continue
    e = {'原因': cause, '类别': name}
    sl = [r for r in rows if r['范围'] == '固态锂硫_全部年份' and r['类别编号'] == code]
    ps = {r['编号'] for r in sl}
    e['固态锂硫'] = {'篇数': len(ps), '2023后': sum(corpus[p]['year'] >= 2023 for p in ps),
                 '最早年份': min((corpus[p]['year'] for p in ps), default=None),
                 '电解质类型': dict(collections.Counter(etype(p) for p in ps)),
                 '组分': dict(collections.Counter(r['改的组分'] for r in sl)),
                 '全部原句': [{'编号': r['编号'], '年份': r['年份'], 'DOI': r['DOI'], '电解质': etype(r['编号']), '原句': r['原句（规范化）'], '命中': r['命中短语']}
                          for r in sorted(sl, key=lambda r: r['年份'])]}
    for src, keys in SRC_SCOPES.items():
        sr = [r for r in rows if r['范围'] == src and r['类别编号'] == code]
        sp = {r['编号'] for r in sr}
        e[src] = {'篇数': len(sp), '前提线索（论文占比）': {k: round(sum(bool(PRE[k].search(full[p])) for p in sp) / len(sp), 2) if sp else None for k in keys},
                  '组分': dict(collections.Counter(r['改的组分'] for r in sr)), '代表原句': pick(sr, 3)}
    report[code] = e

# 主因诊断句：固态锂硫全部年份摘要
DIAG = re.compile(r'rate[- ](?:determining|limiting)|limiting factors?|critical factors?|bottlenecks?|(?:is|are|was|were|remains?) (?:\w+ ){0,2}limited by|governed by|dominated by|primar\w* (?:due to|caused by|attributed to)|main(?:ly)? (?:due to|caused by|attributed to)|origin of|root cause|incomplete (?:conversion|reaction|utilization)|residual (?:s8|sulfur|li2s2)')
CAUSE_KW = {'离子': r'ion(?:ic)?[- ]?(?:transport|conduct|diffusion|flux|percolation)|li\+ (?:transport|flux|diffusion)', '电子': r'electron\w* (?:transport|conduct)|insulat', '反应': r'kinetic|activation|barrier|redox|li2s2|reaction', '接触': r'contact|volume|void|crack|delamina|pressure|chemo-?mechanical'}
diag = []
for pid, r in corpus.items():
    if r['group'] != '固态锂硫': continue
    for s in sentences(r['abstract']):
        if DIAG.search(s) and re.search(r'sulfur|li2s|cathode|s8|conversion', s):
            diag.append({'编号': pid, '年份': r['year'], 'DOI': r['doi'], '电解质': etype(pid), '原句': s,
                         '涉及原因': [k for k, rx in CAUSE_KW.items() if re.search(rx, s)]})
report['_主因诊断句'] = diag
json.dump(report, open(OUT / '_step3a_evidence.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 打印摘要供人工判读
for code, e in report.items():
    if code.startswith('_'): continue
    s = e['固态锂硫']
    print(f"\n### {code} {e['类别']}（{e['原因']}）")
    print(f"  固态锂硫 {s['篇数']} 篇（2023后 {s['2023后']}，最早 {s['最早年份']}）电解质 {s['电解质类型']} 组分 {s['组分']}")
    for src in SRC_SCOPES:
        x = e[src]
        print(f"  {src} {x['篇数']} 篇 前提 {x['前提线索（论文占比）']} 组分 {x['组分']}")
print('\n主因诊断句', len(diag), '条；涉及原因计数', collections.Counter(c for x in diag for c in x['涉及原因']))
