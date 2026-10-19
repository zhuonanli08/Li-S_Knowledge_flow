import os, re, sys, json, pandas as pd
SP = sys.argv[1]
meta = pd.read_csv(SP+'/meta.csv', dtype=str).fillna('').set_index('编号')
pp = pd.read_csv(r'D:/Desktop/课题一锂硫知识流动分析/output/dataset_v2/论文表.csv', dtype=str, low_memory=False).fillna('').set_index('编号')
SE = r"(?:sulfide |thiophosphate |solid[- ]state |solid )?(?:electrolytes?|SSEs?|SEs?|LPSCl|LPSC|Li6PS5Cl|Li6PS5Br|Li3PS4|LPS|Li7P3S11|Li10GeP2S12|LGPS|argyrodites?|thiophosphates?|catholytes?)"
C = {
 'DEC': re.compile(r"(?:decomposition|oxidation|oxidative decomposition|degradation|reduction) of (?:the )?"+SE+r"|"+SE+r"(?: \w+){0,3} (?:decomposition|decomposes|decomposed|degradation|oxidation)", re.I),
 'ACT': re.compile(r"redox[- ]active (?:solid )?(?:electrolytes?|catholytes?|SEs?)|capacity contributions? (?:of|from) (?:the )?"+SE+r"|"+SE+r"(?: \w+){0,3} contribut\w* (?:to )?(?:the |additional |extra )?capacity|electrochemical(?:ly)? activ\w* (?:of )?(?:the )?"+SE+r"|redox activity of (?:the )?"+SE+r"|"+SE+r" (?:as|acts as|serve[sd]? as) (?:an? )?(?:active material|redox mediator|mediator)", re.I),
 'MED': re.compile(r"redox[- ]mediat\w*|\bmediator", re.I),
 'CUT': re.compile(r"(?:cut-?off|upper|lower) (?:potential|voltage)s?[^.]{0,120}(?:decompos|stability|window|side reaction)|(?:decompos|stability window)[^.]{0,120}cut-?off", re.I),
 'IOD': re.compile(r"\bLiI\b|iodide|iodine|Li7P2S8I|Li6PS5I|Li4PS4I", re.I),
 'CTRL': re.compile(r"(?:sulfur|S|Li2S)[- ]free (?:electrode|composite|cathode|control)|without (?:sulfur|S8|Li2S|active material)|(?:SE|electrolyte|LPSCl|Li6PS5Cl|Li3PS4)[–/-](?:C|carbon|VGCF|CNF|super P|acetylene black) (?:composite|electrode)s?|carbon[–/-](?:SE|electrolyte) composite", re.I),
}
rows = []
for f in os.listdir(SP+'/ft'):
    if not f.endswith('.txt'): continue
    w = f[:-4]
    t = open(SP+'/ft/'+f, encoding='utf-8').read()
    t = re.sub(r'-\n(?=[a-z])', '', t); t = re.sub(r'\s+', ' ', t)
    cut = re.search(r'\bReferences\b|\bREFERENCES\b', t[len(t)//2:])
    if cut: t = t[:len(t)//2+cut.start()]
    ta = (pp.at[w,'标题']+' . '+pp.at[w,'摘要']) if w in pp.index else ''
    r = {'编号': w, '年份': meta.at[w,'年份'] if w in meta.index else '', '类型': pp.at[w,'文献类型'] if w in pp.index else '',
         '标题': meta.at[w,'标题'] if w in meta.index else '', 'cell': meta.at[w,'cell_state'] if w in meta.index else '',
         'se': meta.at[w,'se_class'] if w in meta.index else ''}
    for k, rx in C.items():
        r[k] = len(rx.findall(t)); r[k+'_摘'] = len(rx.findall(ta))
    r['review'] = bool(re.search(r'\breview\b|perspective|progress and prospects|recent progress|recent advances|challenges and', r['标题'], re.I)) or r['类型']=='review'
    rows.append(r)
df = pd.DataFrame(rows)
core = df['DEC'] + df['ACT']*3 + df['MED'] + df['CUT']*2
df['score'] = core
df['tier'] = 'T3'
df.loc[(df['DEC_摘']+df['ACT_摘']+df['MED_摘']+df['CUT_摘'] > 0) | (df['ACT'] >= 1) | (core >= 8), 'tier'] = 'T2'
df.loc[(df['ACT_摘'] + df['MED_摘'] > 0) | ((df['DEC_摘'] > 0) & (core >= 5)) | (df['ACT'] >= 2), 'tier'] = 'T1'
df.loc[core < 2, 'tier'] = 'T4'
df.to_csv(SP+'/F/screen.csv', index=False, encoding='utf-8')
print(df['tier'].value_counts().sort_index().to_dict())
print(pd.crosstab(df['tier'], df['review']))
