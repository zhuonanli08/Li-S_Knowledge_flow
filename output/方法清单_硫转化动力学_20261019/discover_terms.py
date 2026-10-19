"""发现用：统计各组"本文做法"句+标题里的高频 2–3 词短语，帮助建方法类别词表；不作为结果。"""
import re, sys, collections
from common import *

sys.stdout.reconfigure(encoding='utf-8')
STOP = set('a an the of and or for to in on with by as at from into via that this these those is are was were be been being '
           'which while than then its their our we here herein it also both such can could may high higher highly enhanced '
           'improved superior excellent effective efficient novel new based using used use through demonstrated show shows '
           'performance batteries battery lithium li sulfur sulphur li-s lithium-sulfur solid-state all-solid-state cell cells '
           'capacity mah g-1 cycles cycle rate ma cm-2 work study'.split())

corpus, tags = load_corpus(), load_tags()
scopes = scope_papers(corpus, tags)
for name, papers in scopes.items():
    if name == '固态锂硫_全部年份':
        continue
    c = collections.Counter()
    n_own = 0
    for r in papers:
        own = own_sentences(r['abstract'])
        n_own += bool(own)
        seen = set()
        for s in own + [norm(r['title'])]:
            w = [t for t in re.findall(r"[a-z0-9][a-z0-9\-]*", s)]
            for k in (2, 3):
                for i in range(len(w) - k + 1):
                    g = w[i:i + k]
                    if g[0] in STOP or g[-1] in STOP or all(x in STOP for x in g):
                        continue
                    seen.add(' '.join(g))
        c.update(seen)
    print(f'\n===== {name}  论文 {len(papers)}，有做法句 {n_own} =====')
    print('；'.join(f'{t}({n})' for t, n in c.most_common(220)))
