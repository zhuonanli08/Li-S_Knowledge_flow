from pathlib import Path
import sys, json, re, collections
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT/'_deps'))
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS
import pandas as pd
from prepare_corpus import norm
data=json.loads((OUT/'corpus.json').read_text(encoding='utf-8'))
stop=set(ENGLISH_STOP_WORDS)|set('herein furthermore moreover respectively demonstrated shows show showing exhibited exhibits exhibit achieved achieve using based highly excellent promising novel high low significantly improved improvement toward towards battery batteries'.split())
vec=CountVectorizer(ngram_range=(2,3),min_df=4,max_df=.65,stop_words=sorted(stop),binary=True,token_pattern=r'(?u)\b[a-z][a-z]+\b')
X=vec.fit_transform([norm(x['abstract']) for x in data]); terms=vec.get_feature_names_out()
rows=[]
for group in ['固态锂硫','液态锂硫','固态锂金属']:
    for period in ['2010-2026','2023-2026']:
        ix=[i for i,r in enumerate(data) if r['group']==group and (period=='2010-2026' or r['year']>=2023)]
        c=X[ix].sum(axis=0).A1
        for j in c.argsort()[::-1][:400]: rows.append({'体系':group,'时段':period,'短语':terms[j],'篇数':int(c[j]),'占比':float(c[j])/len(ix),'分母':len(ix)})
pd.DataFrame(rows).to_csv(OUT/'开放短语_未合并.csv',index=False,encoding='utf-8-sig')
for g in ['固态锂硫','液态锂硫','固态锂金属']:
    print('\n'+g+' 2023-2026')
    for r in [r for r in rows if r['体系']==g and r['时段']=='2023-2026'][:65]: print(r['短语'],r['篇数'])
