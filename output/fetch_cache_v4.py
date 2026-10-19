# 放宽检索式后重拉，存为新缓存（旧缓存保留）
import sys, gzip, json, time, os
sys.path.insert(0, r"D:\Desktop\课题一锂硫知识流动分析")
os.chdir(r"D:\Desktop\课题一锂硫知识流动分析\output")
import requests
_get = requests.get
def get_retry(*a, **k):
    for i in range(10):
        try:
            return _get(*a, **k)
        except requests.exceptions.RequestException as e:
            print(f"  [重试 {i+1}/10] {type(e).__name__}", flush=True); time.sleep(5 * (i + 1))
    raise RuntimeError("OpenAlex 连续 10 次失败")
requests.get = get_retry
import preflight_v2_layered as P

Q = {
 "LiS": ('"lithium sulfur battery" OR "lithium-sulfur batteries" OR "Li-S battery" OR "lithium sulphur battery" '
         'OR "lithium-sulfur cell" OR "lithium sulfur" OR "lithium-sulfur" OR "lithium sulphur" OR "lithium-sulphur" '
         'OR "Li-S" OR "sulfurized polyacrylonitrile" OR "sulfur cathode" OR "sulfur cathodes" OR "Li2S cathode" '
         'OR "lithium polysulfide" OR "lithium polysulfides"'),
 "SSB": ('"solid-state battery" OR "solid-state batteries" OR "all-solid-state" OR "solid-state lithium" '
         'OR "solid-state electrolyte" OR "solid-state electrolytes" OR "solid polymer electrolyte" OR "polymer electrolyte" '
         'OR "polymer electrolytes" OR "LLZO" OR "garnet electrolyte" OR "argyrodite" OR "sulfide electrolyte" '
         'OR "sulfide solid electrolyte" OR "halide electrolyte" OR "thiophosphate" OR "NASICON" OR "LATP" OR "LAGP" '
         'OR "LGPS" OR "thio-LISICON" OR "inorganic solid electrolyte" OR "ceramic electrolyte"'),
 "SPAN": ('"sulfurized polyacrylonitrile" OR "sulfurized PAN" OR "sulfur-polyacrylonitrile" OR "sulfur/polyacrylonitrile" '
          'OR "pyrolyzed polyacrylonitrile" OR "SPAN cathode" OR "SPAN electrode" OR "S-PAN" OR "sulfur-PAN" OR "sulfur@PAN" '
          'OR "sulphurized polyacrylonitrile" OR "polyacrylonitrile-sulfur"'),
}
raw, span_ids = {}, []
for name, q in Q.items():
    print(f"[{name}]", flush=True)
    for w in P.fetch(name, q):
        raw.setdefault(w["id"], w)
        if name == "SPAN": span_ids.append(w["id"])
with gzip.open("preflight_raw_20261010.json.gz", "wt", encoding="utf-8") as f:
    json.dump(raw, f, ensure_ascii=False)
json.dump(span_ids, open("span_ids.json", "w"))
print("\ncached", len(raw), " span", len(span_ids))
