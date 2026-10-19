# -*- coding: utf-8 -*-
"""v2 补池第一步（2026-10-11）：固态锂硫 / 准固态锂硫引用了、但不在检索缓存里的文献，从 OpenAlex 拉元数据存本地
输出 output/cited_meta_v2.json.gz  {"found": {W编号: {id, doi, title, publication_year, type, abstract_inverted_index}},
                                    "missing": [请求了但 OpenAlex 没返回的编号]}
可中断续跑：已拉到的、已确认缺失的不再请求
"""
import os, sys, io, gzip, json, time
os.chdir(r"D:\Desktop\课题一锂硫知识流动分析"); sys.path.insert(0, ".")
_b = io.StringIO(); _o = sys.stdout; sys.stdout = _b
import preflight_v3_cached as V
sys.stdout = _o
import requests

KEY = os.environ.get("OPENALEX_KEY", "")
OUT = "output/cited_meta_v2.json.gz"
SEL = "id,doi,title,publication_year,type,abstract_inverted_index"
short = lambda w: w.rsplit("/", 1)[-1]

cache = json.load(gzip.open(OUT, "rt", encoding="utf-8")) if os.path.exists(OUT) else {"found": {}, "missing": []}
found, missing = cache["found"], set(cache["missing"])
def save():
    with gzip.open(OUT, "wt", encoding="utf-8") as f:
        json.dump({"found": found, "missing": sorted(missing)}, f, ensure_ascii=False)

citing = []
for wid, w in V.raw.items():
    t = w.get("title") or ""
    if V.classify(V.norm(t + " " + V.P.rebuild_abstract(w.get("abstract_inverted_index"))), t, wid)[0] in ("S-LiS", "QSS-LiS"):
        citing.append(wid)
need = set()
for wid in citing:
    for r in V.raw[wid].get("referenced_works") or []:
        r = V.DUP_MAP.get(r, r)
        if r not in V.raw: need.add(short(r))
todo = sorted(need - set(found) - missing)
print(f"引用方 {len(citing):,} 篇；不在检索缓存的被引文献 {len(need):,}；待拉 {len(todo):,}", flush=True)

def get(ids):
    for i in range(20):
        try:
            r = requests.get("https://api.openalex.org/works", params={"filter": "openalex:" + "|".join(ids), "per-page": 50,
                             "select": SEL, "api_key": KEY}, timeout=90)
            if r.status_code == 429:
                time.sleep(10 * (i + 1)); continue
            r.raise_for_status()
            return r.json()["results"]
        except Exception as e:
            print(f"  [重试 {i+1}/20] {type(e).__name__}", flush=True); time.sleep(min(60, 5 * (i + 1)))
    raise RuntimeError("OpenAlex 连续 20 次失败")

for k in range(0, len(todo), 50):
    ids = todo[k:k + 50]
    got = set()
    for x in get(ids):
        s = short(x["id"]); found[s] = x; got.add(s)
    missing.update(set(ids) - got)
    if (k // 50) % 40 == 0 or k + 50 >= len(todo):
        save(); print(f"  {min(k + 50, len(todo)):,}/{len(todo):,}  无元数据累计 {len(missing):,}", flush=True)
    time.sleep(0.1)
save()
print(f"完成：有元数据 {len(found):,}，无元数据 {len(missing):,}", flush=True)
