"""方法清单共用：读语料、选范围、切"本文做法"句。只读问题共现分析的输出，不改动它。"""
from pathlib import Path
import csv, json, re, unicodedata, sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
SRC = ROOT / 'output' / '问题共现分析_20261019'
csv.field_size_limit(10 ** 9)
RECENT = 2023


def norm(s):
    # 与 问题共现分析_20261019/prepare_corpus.py 的 norm 相同，另把 Wiley 标题常用的"─"也视为连字符
    s = unicodedata.normalize('NFKC', str(s)).lower()
    s = re.sub('[‐‑‒–—−─]', '-', s)
    s = re.sub(r'\bli\s*2\s*s\b', 'li2s', s)
    s = re.sub(r'\bs\s*8\b', 's8', s)
    return re.sub(r'\s+', ' ', s).strip()


def sentences(text):
    return re.split(r'(?<=[.!?])\s+(?=[a-z])', norm(text))


# "本文做法"句：作者陈述本文所做的事
OWN = re.compile(
    r'\b(?:here|herein|hereby|in this (?:work|study|paper|contribution|article)|this (?:work|study|paper|strategy|design|approach)'
    r'|we (?:report|propose|design|develop|demonstrate|introduce|construct|fabricate|present|synthesi[sz]e|prepare|employ|use|utilize|'
    r'engineer|adopt|devise|apply|incorporate|explore|tailor|exploit|establish|build|create|achieve|realize|integrate|combine|'
    r'implement|innovatively|rationally|successfully|further|first|systematically|also|then|herein)'
    r'|(?:is|are|was|were|has been|have been) (?:\w+ )?(?:proposed|designed|developed|introduced|constructed|fabricated|synthesi[sz]ed|'
    r'prepared|employed|engineered|incorporated|reported|demonstrated|utilized|adopted|applied|achieved|realized|built|integrated))\b')


def own_sentences(text):
    return [s for s in sentences(text) if OWN.search(s)]


def load_corpus():
    return json.loads((SRC / 'corpus.json').read_text(encoding='utf-8'))


def load_tags():
    """论文号 -> 该篇摘要命中的问题标签集合（来自问题共现分析的逐篇结果）"""
    tags = {}
    with open(SRC / '逐篇主题与证据.csv', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            tags.setdefault(r['编号'], set()).add(r['标签号'])
    return tags


# 各组进入方法清单的范围（见方案D §5）
SCOPES = [
    ('液态锂硫', '液态锂硫', True, {'P03'}),
    ('固态锂金属', '固态锂金属', True, {'P01', 'P04', 'P05'}),
    ('固态锂硫', '固态锂硫', True, {'P03'}),
    ('固态锂硫_全部年份', '固态锂硫', False, None),
]


def scope_papers(corpus, tags):
    out = {}
    for name, group, recent_only, need in SCOPES:
        sel = []
        for r in corpus:
            if r['group'] != group:
                continue
            if recent_only and r['year'] < RECENT:
                continue
            if need is not None and not (tags.get(r['id'], set()) & need):
                continue
            sel.append(r)
        out[name] = sel
    return out
