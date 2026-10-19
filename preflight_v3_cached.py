# -*- coding: utf-8 -*-
"""preflight v3：读本地缓存(output/preflight_raw_*.json.gz)，不再请求 OpenAlex。
相对 v2 的改动：
  1. 液态锂硫 = 所有「锂硫且非固态/准固态」论文，不再要求出现电解液词；另贴 focus 标签(electrolyte/cathode)
  2. 锂硫判定：统一各种破折号，认 Li–S / lithium–sulphur / polysulfide；SPAN 必须大写或写全称
  3. 补通用固态词(all-solid-state / solid electrolyte)；固态锂电池必须提到锂，否则丢弃为 other
  4. 两个口径各出一份：elec=只算偏电解液的液态锂硫；all=全部液态锂硫
  5. (2026-10-10) thio-LISICON 单列；硅-硫/CuS/MoS3 等「硫系转化型」不进任何组；
     本地有全文、摘要认不出电解质的固态锂硫，用全文判断结果补（output/fulltext_sub.json）
  6. (2026-10-11) 规则 v2（PF_RULES=v1 可复现数据集 v1）：
     硫化物全固态默认算锂体系、任意 Li+数字 算提到锂（li_ok）；无摘要的固态电池标题默认锂；固态锂电池补认 superionic conductor；
     锂硫补认老写法（lis_hit：Li-S coin/full-cell、lithium metal–sulfur、Li2S as a positive electrode、文中有锂时的 sulfur electrode 等）
"""
import sys, io, gzip, json, re, contextlib
from collections import Counter, defaultdict
import os; os.environ.setdefault("OPENALEX_KEY", "x")
import preflight_v2_layered as P

CACHE = os.environ.get("PF_CACHE", "output/preflight_raw_20261010.json.gz")
raw = json.load(gzip.open(CACHE, "rt", encoding="utf-8"))

def norm(s): return re.sub(r"[\u2010-\u2015\u2212\u2500\u2501\ufe63\uff0d]", "-", s)
LIS = re.compile(r"lithium.{0,3}sul[fp]h?ur|\bli.{0,3}s (battery|batteries|cell|cells|cathode|cathodes|full cell|pouch|chemistry|system|systems|conversion|redox|electrochemistry)|"
                 r"\bli.{0,3}sul[fp]h?ur|lithium.ion sul[fp]h?ur|sul[fp]h?ur lithium.ion|"
                 r"\bli ?2 ?s.{0,3}(cathode|cathodes|positive electrode|composite cathode)|\bli ?2 ?s.{0,3}based (all.solid.state )?(batter|positive)|\bli2s/s\b|\bli ?2 ?s/li|"
                 r"sulfurized polyacrylonitrile|sulfurized pan|"
                 r"lithium sulfide cathode|sulfur cathode|sulphur cathode|lithium polysulfide", re.I)
LIS_CS = re.compile(r"\bSPAN\b")   # SPAN 必须大写，避免误中 life span
NON_LI = re.compile(r"sodium|\bna.{0,2}s\b|selenium|\bli.{0,2}se\b|magnesium|zinc|potassium|aluminum", re.I)
# SPAN：标题出现，或正文提到 >=2 次，才算 SPAN 路线（只提一次多为对比/背景）
# 缩写 SPAN 必须大写（避免 life span）；全称不分大小写（2026-10-11：原规则区分大小写，标题首字母大写的「Sulfurized Polyacrylonitrile」认不出）
SPAN_RX = re.compile(r"\bSPAN\b|SPAN-?based|(?i:sul(f|ph)uri[sz]ed[- ]?poly\(?acrylonitrile\)?|sul(f|ph)uri[sz]ed[- ]pan\b|sul(f|ph)ur.{0,3}pan\b|"
                     r"sul(f|ph)ur[-/ ]polyacrylonitrile|pyroly[sz]ed.{0,10}pan\b|s@p?pan\b|\bp?pan[-/@]s\b)")
# 复合电解质（2026-10-11 用户定）：聚合物 + 无机物组成的电解质。两种认法：
#   ① 聚合物和无机物连写：PEO-LGPS、LLZTO/PEO、LLZTO@PVDF-HFP、ceramic-in-polymer、LLZTO-filled PEO
#   ② 自称 composite / hybrid 电解质，且是聚合物体系（短语里有 polymer，或文中写了 PEO、PVDF-HFP 等具体聚合物）
# 硫化物 + 粘结剂的「composite electrolyte」膜不算（粘结剂不导锂离子）；「glass-ceramic composite」没有聚合物，不算
_CP = (r"(?<![a-z])(peo|poly\(ethylene oxide\)|pvdf-hfp|pvdf|poly\(vinylidene fluoride[^)]*\)|pan|polyacrylonitrile|ppc|poly\(propylene carbonate\)|"
       r"ptmc|pcl|pegdma|pegda|pegdme|peg|pmma|pvc)(?![a-z])")
_CI = (r"(?<![a-z])(llzto|llzo|llzno|llzao|llzgo|llto|latp|lagp|lgps|lpscl|lpsbr|lps|li6ps5(cl|br|i)|li3ps4|li7p3s11|li10gep2s12|li7la3zr2o12|"
       r"li6\.\d+la3[\w.()]*|li1\.\d+al0\.\d+(ti|ge)[\w.()]*|li0\.\d+la0\.\d+tio3|li3incl6|li3ycl6|li2zrcl6|garnet|nasicon|argyrodite|ceramics?|inorganic|"
       r"sio2|al2o3|tio2|zro2|ceo2|mgo|montmorillonite|halloysite|nano.?fillers?|fillers?)(?![a-z])")
_CPG = r"(" + _CP + r"|(?<![a-z])polymer(ic)?(?![a-z]))"   # 连写时可以只写 polymer（polymer-ceramic、polymer/inorganic）
_CJ = r"\s?[-/@:]\s?"
COMP_JOIN = re.compile(_CPG + _CJ + _CI + "|" + _CI + _CJ + _CPG + "|" + _CPG + r"[- ]in[- ]" + _CI + "|" + _CI + r"[- ]in[- ]" + _CPG + "|" +
                       _CI + r"[- ](filled|reinforced|incorporated|embedded|loaded|enhanced|modified|added|dispersed)[- ](\w+[- ]){0,2}" + _CPG, re.I)
COMP_SAY = re.compile(r"(composite|hybrid|organic.inorganic|inorganic.organic)[- ]((solid|polymer|state|solid-state|polymeric|ceramic|based|type)[- ]){0,3}electrolytes?(?! ?inter)", re.I)
COMP_POLY = re.compile(_CP, re.I); COMP_INORG = re.compile(_CI, re.I)
COMP_ION_POLY = re.compile(r"(?<![a-z])(peo|poly\(ethylene oxide\)|pvdf-hfp|pan|polyacrylonitrile|ppc|ptmc|pcl|pegdma|pegda|pmma)(?![a-z])|polymer electrolyte|solid polymer", re.I)
def composite_hit(text):
    """命中复合电解质时返回命中的原词，否则返回空串"""
    if re.search(r"binder", text, re.I) and not COMP_ION_POLY.search(text): return ""   # 只有粘结剂类聚合物（PVDF 等）
    m = COMP_JOIN.search(text)
    if m: return m.group(0)
    m = COMP_SAY.search(text)
    if m and ("polymer" in m.group(0).lower() or COMP_POLY.search(text)): return m.group(0)   # 自称复合 + 有聚合物即算（用户：告诉你是复合的就算）
    return ""
def is_span(title, text):
    return bool(SPAN_RX.search(title)) or len(SPAN_RX.findall(text)) >= 2
# 「固态」通用词：排除 SEI（solid electrolyte interphase/interface/interlayer）和液态论文里的「固态 Li2S 沉积」之类说法
SOLID_GEN = re.compile(r"all.solid.state|solid.state (lithium.{0,12})?(batter(y|ies)|cells?)|solid.state li[-/]s\b|"
                       r"solid.state electrolytes?(?! inter)|solid electrolytes?(?! inter)|solid polymer electrolytes?", re.I)
LI = re.compile(r"\blithium\b|\bli\b|\bli[-+]|\bli2|\bli3|\bli6|\bli7|li-ion|lithium-ion", re.I)
# v2 准固态口径（2026-10-11 用户确认）：写了 quasi-solid / 凝胶 → 准固态（「quasi-solid-state conversion」是液态里的机理说法，不算；sol-gel 是合成方法，不算）；
# 标题自称固态、只有摘要提到凝胶的仍算固态；用到无机固态电解质或写了 solid polymer electrolyte / 无溶剂 → 固态；
# 只写 PDOL / 原位聚合、没交代状态 → 默认准固态，电解质类型标「原位聚合（状态未写明）」
# 必须紧挨电解质/电池语境：只写「gel」会命中凝胶衍生碳、凝胶粘结剂；只写「in situ polymerization」会命中正极导电聚合物包覆（2026-10-11 核查发现）
_QW = r"(polymer|polymeric|composite|hybrid|gel|ionic|organic|inorganic|single.ion|nanocomposite|ceramic|plastic|flexible|nonflammable|self.healing|li|lithium|sodium)"
QUASI_V2 = re.compile(r"quasi.solid(.state)?[- ](" + _QW + r"[- ]){0,2}(electrolyte|batter|cell|conductor|li\b|li-|lithium|sodium|full|membrane|separator)|"
                      r"semi.solid(.state)?[- ](polymer |composite )?(electrolyte|batter|li\b|li-|lithium)|"
                      r"(?<!sol.)\bgel(led|ated)?[- ]((polymer|composite|state|type|based|ceramic|polymeric)[- ]){0,2}(electrolyte|membrane|separator)|"
                      r"gel.ceramic|\bgpes?\b|ionogel|in.situ gelation", re.I)
# 原位聚合只认 PDOL 本名，或「原位聚合/凝胶化 + 电解质」；「DOL 在负极表面聚合成 SEI」「原位聚合构建 SEI」是液态体系里的界面工程，不算
INSITU_V2 = re.compile(r"\bpdol\b|poly\(1,3-dioxolane\)|poly.?dol\b|"
                       r"in.situ.{0,25}(polymeri|gelat|solidif|cur|cross.?link).{0,40}electrolytes?(?! ?inter)|"
                       r"electrolytes?(?! ?inter).{0,40}in.situ.{0,25}(polymeri|gelat|solidif|cur)|"
                       r"polymeri[sz]ation of (the |a )?(\w+[- ]){0,2}electrolytes?(?! ?inter)|electrochemical(ly)? polymeri[sz]ed electrolyte", re.I)
SOLID_V2 = re.compile(r"(?<!quasi.)(?<!semi.)(all.solid.state|solid.state (lithium.{0,12})?(batter(y|ies)|cells?)|solid.state li[-/]s\b|"
                      r"solid.state electrolytes?(?! inter)|solid electrolytes?(?! inter)|"
                      r"solid.state (ion|ionic|li.ion|lithium.ion|fast.ion) conductors?|inorganic solid.state|solid.state (composite )?(cathodes?|anodes?))|"
                      r"li2s.{0,3}p2s5|li2s.{0,3}\(100.{0,6}p2s5|la3zr2o12|li10\w{0,4}p2s12|li7p3s11|li7p2s8|li4sns4|li4p2s6|li3ocl|"   # 不用宽松的「Li2S…P2S5」：液态里「P2S5 添加剂与 Li2S 反应」会误中
                      r"li1\.\d+al0\.\d+(ti|ge)|li0\.\d+la0\.\d+tio3", re.I)   # 后半段：常见固态电解质分子式（词表里漏掉的）
# OpenAlex 标题里分子式常被拆开（「Li 2 S」「Li 7 La 3 Zr 2 O 12」），v2 先拼回再匹配
def squash(s):
    s = re.sub(r"(?<![a-wyzA-Z])([A-Z][a-z]?) (\d+(?:\.\d+)?)", r"\1\2", s)   # 前面可以是数字或 x（「70Li 2 S」「xLi 2 S」）
    return re.sub(r"(\d) ([A-Z][a-z]?)(?=\d|\b)", r"\1\2", s)
SPE_V2 = re.compile(r"(?<!quasi.)(?<!semi.)solid polymer electrolytes?|(?<!quasi.)solid.state polymer electrolytes?|"
                    r"solvent.free (solid )?(polymer )?electrolytes?|dry (solid )?polymer electrolytes?|all.solid.state polymer", re.I)   # 单写 solvent-free 多是干法电极工艺
HARD_KEYS = ("el_sulfide", "el_oxide", "el_halide", "el_hydride", "el_thiolisicon")
# v2：标题是锌硫、镁硫等的不算锂硫（v1 只认全拼 zinc / magnesium）
NON_LI_V2 = re.compile(r"\b(zn|mg|ca|al|k|na)-s\b", re.I)   # 必须带连字符：「ZnS」是硫化锌催化剂，不是锌硫电池
# v2 的「非锂体系」标题词：v1 的 selenium / aluminum 会误伤「硒掺杂 SPAN」「铝集流体」这类锂硫论文，改成只认其他电池体系的写法
NON_LI_TITLE_V2 = re.compile(r"sodium|\bna.{0,2}s\b|\bli.{0,2}se\b|lithium.selenium|selenium.sul[fp]h?ur batter|magnesium|zinc|potassium|calcium|"
                             r"alumin(i)?um[- ](sul[fp]h?ur|ion|metal batter|batter)", re.I)
# 分组规则版本：v1 = 数据集 v1 的规则；v2（2026-10-11 用户确认）= 硫化物全固态默认算锂体系（不再要求出现「锂」字），
# 且任意「Li+数字」化学式（如 Li4P2S6、Li10GeP2S12）都算提到锂。设环境变量 PF_RULES=v1 可复现 v1
RULES = os.environ.get("PF_RULES", "v2")
LI_V2 = re.compile(r"\blithium\b|\bli\b|\bli[-+]|(?<![a-wyz])li\d|li-ion|lithium-ion|"   # (?<![a-wyz]) 让「75Li2S」「xLi2S」也算
                   r"(?<![a-wyz])li(tfsi|fsi|clo4|pf6|bf4|bob|dfob|no3|bh4|nbo3|pon|coo2|fepo4|mn2o4|ni[0-9x.])", re.I)
# 必须是「硫化物电解质」这类说法；单写 sulfide / argyrodite 不够（argyrodite 也指 Ag8SnSe6 等银基矿物，sulfide 也指金属硫化物催化剂）
SULF_EL = re.compile(r"(?<!poly)(?<!poly-)sul(f|ph)ide[- ](type |based )?(solid[- ])?(state )?(electrolyte(?!s? ?inter)|superionic|super.?ion|ion(ic)?.conduct|glass)|"
                     r"sul(f|ph)ide[- ](based )?all.solid.state|all.solid.state sul(f|ph)ide|thio.?lisicon|"
                     r"argyrodite[- ](type )?(solid[- ])?(state )?electrolyte|thiophosphate (solid )?electrolyte", re.I)
NON_LI_SSB = re.compile(r"sodium|\bna_?\d|\bna[₀-₉]|\bna[-+]|na(clo|pf|bf|tfsi|fsi|no3)|potassium|\bk_?\d|\bk[₀-₉]|\bk[-+]|k(no3|pf6|tfsi|fsi)|"
                        r"magnesium|\bmg\d|calcium|\bzinc|\bzn\b|\bzn\d|\bagi\b|silver iodide|silver.ion|copper.ion|\bag(cf3so3|no3|clo4|tfsi)|"
                        r"ammonium|\bnh4|nascn|\bag\d+sn", re.I)
# 标题明显不是电池的（传感器、太阳能、超级电容、燃料电池、催化研究等）、且标题里没有任何电池语境 → 不进固态锂电池组
# 只看标题：摘要里顺带一句「也可用于传感器」不算。词表经两轮核查收窄（laser/ester/molten 等会误伤激光沉积、聚酯电解质、熔盐处理石榴石）
NONBATT_TITLE = re.compile(r"fuel cell|sofc|\bysz\b|proton|sensor|sensing|electrolysis|electroly[sz]er|thermoelectric|capacitor|solar|photovolt|"
                           r"\bdye|electrochrom|enzym|\bpem\b|\bice\b|planet|mantle|photocatal|electrocatal|organocatal|"
                           r"catalytic (activity|conversion|dehydra|oxidation|reduction|properties|characteristics|performance)|"
                           r"catalysts? for (the )?(oxygen|hydrogen|co2|ethanol|methanol|ammonia|water)|ammonia synthesis|molten sulfide|"
                           r"semiconductor|magnetoelectr|fluoride.ion|oxide.ion|oxygen.ion|hydrogen (evolution|production|storage)|"
                           r"zirconia|yttria|optical parametric|sum.frequency|frequency generation|oscillator|synaptic|neuromorphic|transistor|memristor|"
                           r"ceria|doped ceri|\bgdc\b|\bsdc\b|lsgm|bismuth oxide|cerate", re.I)
BATT_TITLE = re.compile(r"batter|\bcathodes?\b|\banodes?\b|lithium.(ion|metal|secondary|air)|\bli.ion\b|\bli.metal|\bli.(o2|air)\b", re.I)
# 燃料电池、液流电池等标题里也常有 cathode/anode，不能靠电池语境豁免（锂空气除外）
NONBATT_STRONG = re.compile(r"fuel cell|sofc|redox flow|\bpem\b|oxygen reduction reaction", re.I)
LI_AIR_TITLE = re.compile(r"\bli.(o2|air)\b|lithium.(air|oxygen)", re.I)
BATT_CTX = re.compile(r"batter|all.solid.state|solid.state|cathode|anode|electrode", re.I)
# 没有摘要、只能看标题时，明确的固态电池/无机固态电解质标题默认算锂体系（Nature 系论文在 OpenAlex 多半没有摘要）。
# 只写「polymer electrolyte」的还要有电池/电极词或 PEO、PVDF 等锂电常用基体；排除激光、生化、燃料电池等（2026-10-11 抽查 40 篇有三分之一无关后收紧）
NOAB_SSB = re.compile(r"solid.state electrolytes?(?! ?inter)|solid electrolytes?(?! ?inter)|inorganic solid|all.solid.state (lithium |li |rechargeable |thin.film )?(batter|cells?)|"
                      r"solid.state (lithium.{0,12})?batter|superionic|garnet|llzo|llzto|latp|lagp|lisicon|antiperovskite|"   # 不含 NASICON：也可能是钠
                      r"argyrodite[- ](type |based )?(sulfide |solid |solid-state )?(electrolyte|batter|cathode)|li.?argyrodite|"   # 单写 argyrodite 也可能是 Ag8SnSe6
                      r"halide (solid|electrolyte)|sul(f|ph)idic|sul(f|ph)ide.{0,15}electrolyte", re.I)
NOAB_POLY = re.compile(r"polymer electrolyte|\bpeo\b|poly\(ethylene oxide\)", re.I)
NOAB_POLY_OK = re.compile(r"batter|\banode|\bcathode|dendrite|composite|ceramic|filler|\bpeo\b|poly\(ethylene oxide\)|pvdf|poly\(vinylidene|"
                          r"polyacrylonitrile|\bpan\b|pmma|\bppc\b", re.I)
def li_ok(text, solid, title="", ab_len=0):
    if RULES == "v1": return bool(LI.search(text))
    if LI_V2.search(text): return True
    if NON_LI_SSB.search(text): return False
    if solid and SULF_EL.search(text) and BATT_CTX.search(text): return True   # 硫化物电解质 + 电池语境（排除熔盐硫化物电解等）
    # 标题明确是固态电池/固态电解质 → 默认锂；只用于没有摘要或摘要很短（<400 字符，多是截断）的论文——完整摘要都不提锂的多半不是锂体系
    if ab_len >= 400: return False
    return bool(NOAB_SSB.search(title) or (NOAB_POLY.search(title) and NOAB_POLY_OK.search(title)))
# 固态锂电池组补认 superionic conductor（Kamaya 2011「A lithium superionic conductor」等）；只用于非锂硫分支，不影响锂硫论文的液/固判断
SUPERION = re.compile(r"superionic|super.?ion(ic)? conduct|fast.ion(ic)? conduct", re.I)
# v2 补的锂硫写法（老论文、变体写法，v1 认不出）
LIS_V2 = re.compile(r"\bli.{0,3}s (coin|full.cells?|electrodes?|chemistries|technology|technologies)\b|\bli.{0,3}s full.cell|"
                    r"(?<!-)\bli-s\b(?!-| ?(isotop|coordinat|bond|interaction))|"   # 排除「N–Li–S–Mo」化学键写法、Li–S 同位素、Li–S 配位
                    r"lithium.{0,3}metal.{0,3}sul[fp]h?ur|lithium sul[fp]h?ide (cathode|positive)|"
                    r"\bli ?2 ?s (as|as a|as the) (positive electrode|cathode)", re.I)
# 这几种说法本身不带「锂」，要求文中另有锂（或硫化物电解质）才算锂硫
LIS_V2_CTX = re.compile(r"sul[fp]h?ur (positive )?electrodes?|sul[fp]h?ur composite (cathode|electrode)s?|polymer.sul[fp]h?ur composite|"
                        r"dissolved sul[fp]h?ur|sul[fp]h?ur.carbon nano.?composites? (as )?(the )?cathode|"
                        r"sul[fp]h?ur as (the )?(cathode|positive)|sul[fp]h?ur.based (cathode|positive)", re.I)
# 新写法只看标题：摘要里顺带一句「也在 Li-S 全电池里试了」会把锂负极、硫化物电解质论文误判成锂硫（2026-10-11 核查发现）
def lis_hit(text, title):
    if LIS.search(text) or LIS_CS.search(text): return True
    if RULES == "v1": return False
    return bool(LIS_V2.search(title)) or (bool(LIS_V2_CTX.search(title)) and bool(LI_V2.search(text) or SULF_EL.search(text)))
# 标题明确写了「锂硫」（不含 SPAN 全称、sulfur cathode：钠硫/镁硫论文也这么写）——用于钠/镁等标题的豁免和硫系转化型的豁免
LIS_LI = re.compile(r"lithium.{0,3}sul[fp]h?ur|\bli.{0,3}s (battery|batteries|cell|cells|cathode|cathodes|full cell|pouch|chemistry|system|systems|conversion|redox|electrochemistry)|"
                    r"\bli.{0,3}sul[fp]h?ur|lithium.ion sul[fp]h?ur|sul[fp]h?ur lithium.ion|"
                    r"\bli ?2 ?s.{0,3}(cathode|cathodes|positive electrode|composite cathode)|\bli ?2 ?s.{0,3}based (all.solid.state )?(batter|positive)|\bli2s/s\b|\bli ?2 ?s/li|"
                    r"lithium sulfide cathode|lithium polysulfide", re.I)
def lis_title(title):
    if RULES == "v1": return bool(LIS.search(title))
    return bool(LIS_LI.search(title)) or bool(LIS_V2.search(title))
# v2：「lithium-polysulfide electrolyte」（液态锂硫的多硫化物电解液）里含「sulfide electrolyte」，会被旧词表当成硫化物固态电解质（v1 就有的漏洞）
EL_SULFIDE_V2 = re.compile(r"(?<!poly)(?<!poly-)sul(f|ph)ide (solid )?(state )?electrolytes?|(?<!poly)(?<!poly-)sul(f|ph)ide solid|li2s.{0,2}p2s5|p2s5.{0,2}li2s|thiophosphate|"
                           r"lgps|argyrodite|li6ps5|li3ps4|li7p3s11|li10gep2s12|li[0-9.]+ps[0-9.]+(cl|br|i)\b|li4sns4|lisipscl", re.I)
# 「这篇是不是在讲电解质」：只看标题，液态锂硫和固态锂电池用同一标准（2026-10-10 用户确认）
EL_TITLE = re.compile(r"electrolyte|solvent|solvat|lithium salt|\bsalts?\b|additive|ionic liquid|ionogel|ion conduct|"
                      r"superionic|conductor|argyrodite|garnet|llzo|llzto|latp|lagp|nasicon|thiophosphate|li6ps5|li3ps4|"
                      r"li10gep2s12|lgps|li7p3s11|li3incl6|li3ycl6|li2zrcl6|\bpeo\b", re.I)
# 正极路线（按活性物质）：SPAN > Li2S 正极 > 有机硫 > 单质硫复合；都没有 → 未标明
ROUTE_LI2S = re.compile(r"\bli ?2 ?s.{0,6}(cathode|cathodes|positive electrode|composite cathode|nanocomposite)|lithium sulfide (cathode|positive|electrode)|"
                        r"\bli ?2 ?s.{0,3}based (cathode|positive|electrode|batter|all)|\bli2s@|\bli2s/(c|carbon|graphene|cnt)\b|li2s/li|pre.?lithiated sulfur", re.I)
ROUTE_ORG = re.compile(r"organosulfur|organo-sulfur|sulfur.rich (polymer|copolymer)|inverse vulcani[sz]|sulfur copolymer|poly\(sulfur", re.I)
ROUTE_SC = re.compile(r"sulfur[- /]carbon|carbon[- /]sulfur|\bs/c\b|\bs-c composite|\bs@|sulfur@|\bs/kb\b|\bs-kb\b|ketjen|elemental sulfur|\bs8\b|"
                      r"sulfur (cathode|electrode|composite|host|loading|content|utilization|particles?)|"
                      r"sulfur.{0,25}(cnt|carbon nanotube|graphene|rgo|acetylene black|super p|vgcf|porous carbon|mesoporous carbon|carbon black)", re.I)

SPAN_IDS = set(json.load(open("output/span_ids.json")))
_ft = json.load(open("output/fulltext_labels.json", encoding="utf-8")) if os.path.exists("output/fulltext_labels.json") else {}
FT_SUB, FT_ROUTE = _ft.get("sub", {}), _ft.get("route", {})

# 去重：同一论文被 OpenAlex 收成多个编号（预印本+正式版等）→ 只留参考文献最多的那个，其余并入
def _tkey(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())
_by = defaultdict(list)
for _w, _x in raw.items():
    _k = _tkey(_x.get("title"))
    if len(_k) >= 25: _by[_k].append(_w)
DUP_MAP = {}
for _k, _ws in _by.items():
    if len(_ws) < 2: continue
    _ws.sort(key=lambda w: (-len(raw[w].get("referenced_works") or []), not raw[w].get("abstract_inverted_index"), w))
    for _w in _ws[1:]:
        if abs((raw[_w].get("publication_year") or 0) - (raw[_ws[0]].get("publication_year") or 0)) <= 1:
            DUP_MAP[_w] = _ws[0]


EXTRA = {
  "el_thiolisicon": re.compile(r"thio.?lisicon|li3\.25ge|li4ges4|li4-xge1-xpxs4|li3\.4si0\.4p0\.6s4|li3\.33ge", re.I),
  "el_sulfide": re.compile(r"sulfide (solid )?(state )?electrolytes?|sulfide solid|li2s.{0,2}p2s5|thiophosphate|lgps|argyrodite|li6ps5|li3ps4|li7p3s11|li10gep2s12|"
                           r"li[0-9.]+ps[0-9.]+(cl|br|i)\b|li4sns4|lisipscl|p2s5.{0,2}li2s", re.I),
  "el_oxide":   re.compile(r"garnet|\bllzo\b|\bllzto\b|\bllto\b|\blatp\b|\blagp\b|nasicon|\blipon\b|oxide (solid )?(state )?electrolytes?", re.I),
  "el_halide":  re.compile(r"halide (solid )?(state )?electrolytes?|chloride (solid )?(state )?electrolytes?|oxychloride|"
                           r"li3incl6|li3ycl6|li3ybr6|li2zrcl6|li3sccl6|lialcl4|li3ercl6|li3hocl6|litaocl", re.I),
  "el_hydride": re.compile(r"libh4|li4\(bh4\)3i|borohydride|complex hydride|closo|li-b-h|li2b12h12|licb11|licb9|hydride (solid )?electrolytes?", re.I),
  "el_polymer": re.compile(r"\bpeo\b|polymer electrolytes?|solid polymer|poly\(ethylene oxide\)|"
                           r"polymer[- ](nano)?composite electrolytes?|composite polymer electrolytes?|polymer.ceramic electrolytes?|polymer electrolyte membranes?", re.I),
  # 凝胶/原位聚合（与 v2 的 el_quasi 合并，算准固态）
  "el_quasi":   re.compile(r"in.situ gell?(ed|ation)|gel.ceramic|\bpdol\b|poly\(1,3-dioxolane\)|electrochemical(ly)? polymeri[sz]|"
                           r"polymeri[sz]ation of .{0,30}electrolytes?|gel(led)? (polymer )?electrolytes?", re.I),
}
def tag_all(text):
    t = P.tag(text)
    for k, rx in EXTRA.items():
        if rx.search(text): t.add(k)
    return t

# 硫系转化型（硅-硫、Li2S-Si、CuS、CuFeS2、MoS3、FeS2、SeS2 等）：用户定「先不算」，不进任何组。只看标题，避免误伤摘要里提到金属硫化物催化剂的锂硫论文
SX_TITLE = re.compile(r"silicon.sulfur|\bsi.s batter|li2s.si\b|copper sulfide|\bcus\b|cufes_?2|\bmos_?3\b|molybdenum trisulfide|\bfes_?2\b|ses ?_?2|"
                      r"lithium.chalcogen|metal sulfide cathode|conversion cathode", re.I)
# v2 补：Li2S 正极 + 硅负极写成整句的标题（如「Lithium Sulfide Positive and Silicon Negative ...」），同属用户定的 Li2S-Si 不计
SX_LI2S_SI = re.compile(r"(lithium sul[fp]h?ide|\bli ?2 ?s\b).{0,40}silicon|silicon.{0,40}(lithium sul[fp]h?ide|\bli ?2 ?s\b)|"
                        r"\bpyrite\b(?![- ](sul[fp]h?ur|s\b))", re.I)   # 纯黄铁矿（FeS2）正极同属硫系转化型；「pyrite-sulfur 复合」含单质硫，仍算锂硫
# v2 补（2026-10-11 用户确认）：金属硫化物作正极/电极活性物质（NiS、Sb2S3、Fe–P–S、CoS2、Bi2S3、VS4…）同属硫系转化型，不计；
# 锂硫论文里把它们当催化剂（标题写了锂硫）不排除；「硫化物 + 单质硫」复合正极含单质硫，不排除；TiS2 等嵌入型正极不在此列
SX_MS_V2 = re.compile(r"\b(nis2?|ni3s2|nickel sulfides?|sb2s3|antimony sulfides?|fe-?p-?s|fes|iron sulfides?|cos2|co9s8|cobalt sulfides?|bi2s3|bismuth sulfides?|vs4|cu2s)\b"
                      r".{0,60}(cathodes?|positive|electrodes?|batter)|(cathodes?|electrodes?) (based on |of |with )?\S{0,20}\b(nis2?|sb2s3|fes|cos2|bi2s3|vs4)\b", re.I)
# 金属硫化物只是配角的情况不排除：含单质硫的复合正极、硫正极的载体/催化剂、多硫化物、「…-sulfur battery」、Li2S 正极
SULFUR_COMPOSITE = re.compile(r"(sulfide|pyrite)[- ](and )?sul[fp]h?ur|sul[fp]h?ur[- ](and )?\w+ sulfide|sul[fp]h?ur[- ]based|"
                              r"sul[fp]h?ur (cathode|host|electrode)|host for (the )?sul[fp]h?ur|polysulfide|sul[fp]h?ur batter|\bli ?2 ?s\b", re.I)
def is_sx(title):
    # Li2S + 硅：本身由「Li2S 和硅同时出现」定义，不看一般的锂硫豁免；但标题明确写了 lithium-sulfur / Li-S 电池的（如锂硫+硅硫综述）仍算锂硫
    if RULES != "v1" and SX_LI2S_SI.search(title) and not re.search(r"lithium.{0,3}sul[fp]h?ur\b|\bli.{0,3}s (batter|cell)", title, re.I): return True
    if RULES != "v1" and SX_MS_V2.search(title) and not lis_title(title) and not SULFUR_COMPOSITE.search(title): return True
    return bool(SX_TITLE.search(title)) and not lis_title(title)

def classify(text, title="", wid=None):
    title = norm(title)
    if RULES != "v1": text, title = squash(text), squash(title)
    if wid in DUP_MAP or is_sx(title): return None, None, None, None
    t = tag_all(text)
    if RULES != "v1" and "el_sulfide" in t and not EL_SULFIDE_V2.search(text): t.discard("el_sulfide")   # 只因「polysulfide electrolyte」命中的不算
    has_ab = len(text.strip()) > len(title.strip()) + 3   # text = 标题 + 摘要；只比标题长一点 = 没有摘要
    # 标题出现钠/硒/镁等且标题本身没写锂或 Li-S → 视为非锂体系（防钠硫论文摘要里顺带提锂硫）
    non_li_title = NON_LI.search(title) if RULES == "v1" else (NON_LI_TITLE_V2.search(title) or NON_LI_V2.search(title))
    li_in_title = re.search("lithium", title, re.I) or (RULES != "v1" and re.search(r"\bli-s\b", title, re.I))   # v2：标题写了 Li–S（如「Li–S 和 Na–S」）也算
    is_lis = lis_hit(text, title) and not (non_li_title and not li_in_title and not lis_title(title))
    insitu_default = False
    if RULES == "v1":
        solid = any(k in t for k in P.SOLID_KEYS + ("el_hydride", "el_thiolisicon")) or bool(SOLID_GEN.search(text))
        quasi = "el_quasi" in t
    else:   # 准固态口径（见 QUASI_V2 上方注释）：三态互斥
        qt, qa = bool(QUASI_V2.search(title)), bool(QUASI_V2.search(text))
        hard = any(k in t for k in HARD_KEYS) or bool(SOLID_V2.search(text)) or bool(SPE_V2.search(text))
        insitu = bool(INSITU_V2.search(text))
        title_solid = bool(SOLID_V2.search(title)) and not qt
        if qt or (qa and not title_solid): state = "Q"
        elif hard: state = "S"
        elif "el_polymer" in t and not insitu: state = "S"   # 写了 PEO 等聚合物电解质、没提凝胶 → 固态
        elif insitu: state = "Q"; insitu_default = True       # 只写 PDOL / 原位聚合、没交代状态 → 默认准固态，打标签
        else: state = "L"
        solid, quasi = state == "S", state == "Q"
    if is_lis:
        if quasi and not solid: form = "QSS"
        elif solid: form = "S"
        else: form = "L"
        if wid in SPAN_IDS or is_span(title, text): route = "SPAN"
        elif "ca_li2s" in t or ROUTE_LI2S.search(text): route = "Li2S"
        elif ROUTE_ORG.search(text): route = "orgS"
        elif "ca_sc" in t or "ca_ss" in t or ROUTE_SC.search(text): route = "S-C"
        else: route = FT_ROUTE.get(wid, "route?")   # 摘要认不出时，用本地全文判断结果
        if RULES != "v1" and form == "S" and composite_hit(text): sub = "composite"   # 复合放在最前面判
        elif "el_thiolisicon" in t: sub = "thiolisicon"
        elif "el_sulfide" in t: sub = "sulfide"
        elif "el_halide" in t: sub = "halide"
        elif "el_hydride" in t: sub = "hydride"
        elif "el_oxide" in t: sub = "oxide"
        elif "el_polymer" in t: sub = "polymer"
        elif quasi: sub = "gel"
        elif form == "L": sub = "ether" if "el_liquid" in t else "liq"
        else: sub = FT_SUB.get(wid, "el?")   # 摘要认不出时，用本地全文判断结果（只有本地有全文的才有）
        if RULES != "v1" and form == "QSS": sub = "insitu" if insitu_default else "gel"
        focus = "elec" if EL_TITLE.search(title) else "other"
        L1 = f"{form}-LiS"; L2 = f"{L1}|{route}"; L3 = f"{L2}|{sub}"
        return L1, L2, L3, focus
    solid_lib = solid or (RULES != "v1" and bool(SUPERION.search(text)))
    nonbatt = RULES != "v1" and ((bool(NONBATT_TITLE.search(title)) and not BATT_TITLE.search(title)) or
                                 (bool(NONBATT_STRONG.search(title)) and not LI_AIR_TITLE.search(title)))
    if (solid_lib or quasi) and li_ok(text, solid, title, len(text) - len(title)) and not nonbatt:
        if RULES != "v1" and composite_hit(text): sub = "composite"   # 准固态的下面会改回 gel / insitu
        elif "el_thiolisicon" in t: sub = "thiolisicon"
        elif "el_sulfide" in t: sub = "sulfide"
        elif "el_halide" in t: sub = "halide"
        elif "el_hydride" in t: sub = "hydride"
        elif "el_oxide" in t: sub = "oxide"
        elif "el_polymer" in t: sub = "polymer"
        elif quasi: sub = "gel"
        else: sub = "other-solid"
        if RULES != "v1" and quasi: sub = "insitu" if insitu_default else "gel"
        return "S-LiB", f"S-LiB|{sub}", f"S-LiB|{sub}", ("elec" if EL_TITLE.search(title) else "other")
    return None, None, None, None

nodes = {"all": ({}, {}, {}), "elec": ({}, {}, {})}
cnt = Counter(); focus_cnt = Counter()
for wid, w in raw.items():
    text = norm((w.get("title") or "") + " " + P.rebuild_abstract(w.get("abstract_inverted_index")))
    a, b, c, f = classify(text, w.get("title") or "", wid)
    if a is None:
        cnt["unclassified"] += 1
        if wid in DUP_MAP: cnt["重复收录(并入)"] += 1
        elif is_sx(norm(w.get("title") or "")): cnt["硫系转化型(不计)"] += 1
        continue
    cnt[a] += 1
    if a == "L-LiS": focus_cnt[f] += 1
    for k in ("all", "elec"):
        if k == "elec" and a == "L-LiS" and f != "elec": continue
        for d, v in zip(nodes[k], (a, b, c)): d[wid] = v

print(f"总 {len(raw):,} 篇；未归类 {cnt['unclassified']:,} ({cnt['unclassified']/len(raw):.1%})")
print({k: v for k, v in cnt.items() if k != 'unclassified'}, " 液态锂硫 focus:", dict(focus_cnt))
res = {}
for k in ("all", "elec"):
    for i, name in enumerate(("L1", "L2", "L3")):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            e = P.report_level(f"[{k}] {name}", nodes[k][i], raw)
        open(f"output/preflight_v3_{k}_{name}.txt", "w", encoding="utf-8").write(buf.getvalue())
        res[f"{k}_{name}"] = {f"{a}->{b}": v for (a, b), v in e.items()}
json.dump({"counts": dict(cnt), "focus": dict(focus_cnt), **res},
          open("output/preflight_v3_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
