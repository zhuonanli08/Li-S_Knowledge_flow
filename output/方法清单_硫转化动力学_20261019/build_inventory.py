"""第 ② 步：三体系方法清单（主问题 = 固态锂硫正极硫转化动力学受限）。
只从标题和"本文做法"句识别方法；篇数只说明用得多不多，不说明有效；不做复用判断（第 ③ 步）。
不适用于主线的结果（锂负极专用方法、负极侧界面层、实为锂沉积动力学的论文）单独写到 不适用_单独存/。
"""
import re, sys, json, collections
from common import *

sys.stdout.reconfigure(encoding='utf-8')

# (编号, 原因, 方法类别, 正则)  —— 正则作用于规范化(小写)的标题和"本文做法"句
CAUSES = ['反应本身慢', '电子到不了反应面', '离子到不了反应面', '接触丢失', '锂负极专用']
VOCAB = [
    ('M01', '反应本身慢', '单原子/原子级分散催化剂',
     r'single[- ]atom\w*|single (?:\w+ )?atoms?|atomically dispersed|dual[- ]atom\w*|diatomic|atomic (?:metal|cobalt|iron|nickel|co|fe|ni|zn|mn|cu) sites?|\b(?:fe|co|ni|zn|mn|cu|mo|w)[- ]n[- ]?[cx]?4?\b sites?|m[- ]n[- ]c\b|metal[- ]n(?:itrogen)?[- ]c(?:arbon)? sites?'),
    ('M02', '反应本身慢', '金属化合物催化剂/极性宿主（含异质结构、缺陷、MXene、MOF）',
     r'electrocatalys\w*|bimetallic|metal sites?|\bcatalys\w*|\bcatalytic\w*|heterostructur\w*|heterojunction\w*|hetero[- ]?interface\w*|built[- ]in (?:\w+ )?electric fields?|d[- ]band|p[- ]band|orbital hybridi\w*|(?:oxygen|sulfur|anion|cation|selenium) vacanc\w*|high[- ]entropy|mxenes?|ti3c2|quantum dots?'),
    ('M03', '反应本身慢', '氧化还原介体',
     r'redox mediat\w*|\bmediators?\b|redox[- ]active (?:electrolyte|catholyte|additive|species|anion|interphase|solid electrolyte)|triiodide|\bi3-|iodine redox|iodide redox'),
    ('M04', '反应本身慢', '改变活性物形态/反应路径（SPAN、有机硫、小分子硫、Se 掺杂、Li₂S 正极）',
     r'sulfurized polyacrylonitrile|\(span\)|\bspan\b(?! of)|organosulfur\w*|organic sulfur|sulfur[- ]rich (?:polymer|copolymer)|inverse vulcani\w*|small[- ]molecule sulfur|small sulfur|short[- ]chain sulfur|covalent(?:ly)? (?:bonded |bound )?sulfur|sulfur copolymer|selenium[- ]doped|se[- ]doped|\bses2\b|sulfur[- ]selenium|li2s cathodes?|li2s[- ]based|li2s particles?|li2s nano\w*|lithium sulfide cathodes?|polysulfide catholyte|amorphous sulfur|sulfur nanoparticles?|\bte[- ]dop\w*|tellurium[- ]dop\w*|partially lithiated|(?:lithium )?polysulfide cathodes?|li2sx cathodes?|li2s(?: \(\w+\))? cathodes?|activated li2s'),
    ('M05', '反应本身慢', '电解液/溶剂化/添加剂调控',
     r'solvation|solvating|coordination (?:entropy|structure|environment) of li|li\+ coordination|\bsolvents?\b|high[- ]donor|donor number|electrolyte additives?|\badditives?\b|localized high[- ]concentration|high[- ]concentration electrolyte|electrolyte (?:design|engineering|formulation|regulation)|co[- ]solvent|\bdiluents?\b|fluorinated (?:ether|solvent)'),
    ('M06', '电子到不了反应面', '碳宿主/导电碳网络',
     r'carbon nanotubes?|\bcnts?\b|graphene|\brgo\b|porous carbon|carbon nanofib\w*|hollow carbon|carbon cloth|carbon host|conductive carbon|ketjen\w*|super ?p\b|carbon black|vapor[- ]grown carbon|\bvgcf\b|carbon matrix|carbon framework|mesoporous carbon|n-doped carbon|nitrogen-doped (?:porous )?carbon|carbon spheres?|graphitic carbon|carbon nanosheets?|carbon additives?|acetylene black|carbon paper|carbon felt|carbon skeleton|carbon scaffold'),
    ('M07', '电子到不了反应面', '导电聚合物',
     r'pedot|polypyrrole|\bppy\b|polyaniline|\bpani\b|conductive polymers?|conducting polymers?|polythiophene'),
    ('M08', '电子到不了反应面', '混合离子-电子导体',
     r'mixed (?:ionic[- ]electronic|ion[- ]electron|electronic[- ]ionic) conduct\w*|mixed conduct\w*|\bmiecs?\b|mixed ionic'),
    ('M09', '离子到不了反应面', '复合正极内离子通路/三相界面设计',
     r'triple[- ]phase|tri[- ]phase|three[- ]phase (?:interface|boundar\w*|contact)|catholyte|in[- ]situ (?:formed|generated|grown) (?:solid )?electrolyte|electrolyte (?:coating|coated|layer) on|coated with (?:a )?(?:thin )?(?:solid )?electrolyte|ion(?:ic)?[- ](?:conducting|conductive|transport) (?:network|pathway|channel|highway)s?|percolat\w*|li2s[- ]lii|lii[- ]li2s|solid solutions? of li2s|ionic(?:ally)? conductive domains?'),
    ('M10', '离子到不了反应面', '无机电解质体相：新组成与改性（掺杂、取代、富卤）',
     r'(?:novel (?:\w+ )?(?:solid )?electrolyte|new (?:class of )?(?:\w+[- ])?(?:electrolytes?|conductors?|chlorides?)|superionic conduct\w*|(?<![a-z])dop\w*|substitut\w*|aliovalent|halogen[- ]rich|cl[- ]rich|br[- ]rich|i[- ]rich|anion (?:mixing|engineering)|lattice engineering)'),
    ('M11', '离子到不了反应面', '聚合物/复合电解质（基体、填料、交联）',
     r'polymer electrolytes?|\bpeo\b|poly ?\(ethylene oxide\)|polyethylene oxide|pvdf|poly ?\(vinylidene|polymer matri\w*|composite (?:solid |polymer |solid-state )?electrolytes?|ceramic fillers?|inorganic fillers?|\bfillers?\b|single[- ]ion conduct\w*|polycarbonate|\bppc\b|polymer[- ]in[- ]ceramic|ceramic[- ]in[- ]polymer|cross[- ]?link\w*|block copolymer|poly(?:cationic|anionic|ionic|meric) (?:solid )?electrolytes?|polymer[- ](?:solid )?electrolyte composites?|composite (?:solid )?separators?|ceramic[- ]rich'),
    ('M12', '离子到不了反应面', '含液或准固态成分（离子液体、增塑剂、原位聚合、凝胶）',
     r'ionic liquids?|succinonitrile|plastic crystal|deep eutectic|in[- ]situ polymeri\w*|1,3-dioxolane|\bdol\b|plastici[sz]\w*|(?<!sol-)(?<!sol )\bgel\b(?![- ]crystalline)|gel polymer|quasi[- ]solid|liquid (?:electrolyte )?(?:wetting|additive|addition)|trace (?:amounts? of )?liquid'),
    ('M13', '离子到不了反应面', '颗粒尺寸与混合/合成工艺',
     r'ball[- ]mill\w*|mechanochemic\w*|mechanical milling|high[- ]energy milling|co[- ]milling|planetary milling|particle sizes?|nano[- ]?siz\w*|downsiz\w*|size reduction|wet[- ]chemi\w*|solution[- ]process\w*|solution[- ]based|liquid[- ]phase (?:synthesis|process\w*|method|route)|vapor[- ]phase|melt[- ]diffusion|melt[- ]quench\w*|spray[- ]dry\w*|(?:rapid|facile|scalable|one[- ]step|ultrafast|low[- ]cost|green) (?:synthesis|preparation)|joule[- ]heat\w*|sinter\w*|pulveriz\w* (?:to prepare|method)|solution[- ]precipitation|precipitation process|anneal\w* process|annealing (?:temperature|condition)s?|aqueous synthesis|low[- ]temperature synthesis|synthesis route|spray[- ]deposit\w*'),
    ('M14', '离子到不了反应面', '电极/电解质结构设计（梯度、三维骨架、取向、厚电极、干法）',
     r'gradient\w*|three[- ]dimensional(?:ly)? (?:\w+ )?(?:architecture|framework|structure|host|network|skeleton|scaffold|porous|electrode|current collector|interconnected)|\b3d (?:\w+ )?(?:architecture|framework|structure|host|network|skeleton|scaffold)|vertical\w* aligned|tortuosit\w*|thick (?:cathode|electrode)s?|free[- ]?standing|self[- ]support\w*|binder[- ]free|dry[- ]process\w*|dry electrode|solvent[- ]free (?:electrode|process\w*|fabricat\w*)|(?:electrode|cathode) architecture\w*|bilayer|multilayer\w*|sandwich\w*|high[- ]oriented|oriented (?:\w+ )?(?:framework|nanofibers?|channels?|structure)'),
    ('M15', '接触丢失', '界面层/包覆层/中间层（含隔膜修饰）',
     r'interlayers?|inter-layers?|coatings?\b|coated\b|buffer layers?|protective layers?|protection layers?|artificial (?:sei|interphase|layer|solid electrolyte interphase|cathode electrolyte interphase)|interphase engineering|interface engineering|interfacial engineering|interfacial layers?|surface modification|surface engineering|separator modification|modified separators?|functional separators?|multifunctional separators?|separator coating|atomic layer deposition|\bald\b|passivation layers?|core[- ]shell|encapsulat\w*|surface treatment|li2co3 (?:removal|elimination)|(?:remov|eliminat)\w* (?:of )?(?:the )?li ?2 ?co ?3|cleaning strategy|sputter\w*|plasma[- ](?:assisted|treat\w*)'),
    ('M16', '接触丢失', '软质/黏弹/可变形材料与粘结剂',
     r'\bbinders?\b|elastomer\w*|viscoelastic\w*|\belastic\w*|deformab\w*|self[- ]heal\w*|stretchab\w*|ductil\w*|soft (?:electrolyte|polymer|matrix|phase|interface|interlayer|solid)|low (?:young|modulus)|compliant|strain[- ]accommodat\w*|stress[- ]relie\w*|buffer(?:ing)? (?:the )?volume'),
    ('M17', '接触丢失', '压力/温度等外部条件',
     r'stack(?:ing)? pressures?|external pressures?|operating pressures?|low[- ]pressure|high[- ]pressure|pressure[- ]free|pressureless|uniaxial pressure|hot[- ]press\w*|isostatic\w*|cold[- ]press\w*|elevated temperatures?|high[- ]temperature operation|operat\w* (?:at )?(?:elevated|high) temperature|atmospheric[- ]pressure|ambient pressure'),
    ('X01', '锂负极专用', '锂负极专用方法（亲锂层、锂宿主、合金负极、锂表面人工 SEI）',
     r'lithiophilic\w*|lithophilic\w*|lithiophobic\w*|prelithiat\w*|composite (?:[\w-]+ )?anodes?|(?:li|lithium)[- ]\w+ alloys?|\w+[- ]based li(?:thium)? alloys?|\bli alloys?|li ?x ?si anode|silicon anodes?|\bsi anodes?|\bli(?:thium)? host|host for (?:li|lithium)|li(?:thium)? metal host|3d (?:\w+ )?(?:current collector|host) for|alloy anodes?|li[- ]in anode|li[- ]al anode|anode[- ]free|current collectors?|(?:on|at) (?:the )?li(?:thium)?(?: metal)? (?:anode )?surface|li(?:thium)? anode surface|li(?:thium)? metal surface|li(?:thium)? (?:metal )?anode interface|anode interlayer|anode protection|dendrite[- ]free|dendrite suppression|suppress(?:ing|es|ion of)? (?:the )?(?:li(?:thium)? )?dendrite\w*'),
]
PATS = [(c, cause, name, re.compile(rx)) for c, cause, name, rx in VOCAB]
SAC = PATS[0][3]
COMPOUND = re.compile(r'heterostructur\w*|heterojunction\w*|hetero[- ]?interface\w*|built[- ]in electric field|vacanc\w*|high[- ]entropy|mxenes?|ti3c2|quantum dots?|(?:metal )?(?:sulfide|oxide|nitride|phosphide|selenide|carbide|boride|telluride)s?\b|\b(?:mo|w|co|ni|fe|v|ti|mn|cu|zn|nb|sn)[a-z]?\d*(?:s|se|o|n|p|c)\d|\b(?:co|ni|fe|mo|w|v|ti|mn|cu|zn|nb)(?:p|s|se|n|o)\b')
ELECTROLYTE = re.compile(r'electrolyte|conductor|\b[sgc]pes?\b|\bpes\b|\bcses?\b|chlorides?|hydroborate|borohydride|li3n|superionic|lisicon|perovskite|llto|li3ocl|\bsses?\b|\bses\b|argyrodite|garnet|llzt?o|latp|lagp|lgps|li6ps5|li3ps4|li7p3s11|halide|nasicon|antiperovskite|li3incl6|li3ycl6|thio-lisicon')
ANODE = re.compile(r'\banodes?\b|\blmas?\b|molten li\w*|li[- ]graphite|li(?:thium)?[- ]metal|\bli metal|dendrit\w*|plating|stripping|lithiophilic|\bsei\b|anode[- ]free|li(?:thium)? (?:deposition|nucleation)')
CATHODE = re.compile(r'cathodes?\b|positive electrode|sulfur|sulphur|\bs8\b|li2s|polysulfide|shuttl\w*|conversion|redox|\bcei\b|ncm|nmc|lini|licoo2|lifepo4|lfp\b')
SEPARATOR = re.compile(r'separator|interlayer|\bpp\b|polypropylene membrane')
LIQUID_ANODE_KINETICS = re.compile(r'plating|stripping|deposition|nucleation')
SULFUR_CONV = re.compile(r'sulfur|sulphur|polysulfide|li2s|\bs8\b|redox|conversion')


def lithium_iodide_mediator(s):
    return re.search(r'\blii\b', s) and re.search(r'mediat|redox|catalys', s)


def match_classes(sents, scope=''):
    """sents: [(来源, 句子)]；返回 {类别编号: (来源, 句子, 命中短语)}，每类取第一处命中"""
    hits = {}
    for code, cause, name, pat in PATS:
        for src, s in sents:
            m = pat.search(s)
            if code == 'M03' and not m and lithium_iodide_mediator(s):
                m = re.search(r'\blii\b', s)
            if code == 'M10' and m and not (ELECTROLYTE.search(s) and not re.search(r'catalys|carbon|host|cathode material', s)):
                m = None
            if code == 'M09' and m and not re.search(r'cathode|catholyte|sulfur|sulphur|li2s|electrode|active material', s):
                m = None  # 只算正极内的离子通路；电解质膜内的通道归 M11
            if code == 'M11' and not m and re.search(r'electrolyte|conductor|ion conduct', s):
                m = re.search(r'polyether\w*|polycaprolactone|\bpcl\b|polyrotaxane|polyzwitterion\w*|poly\(\w+|polymeric|\bspes?\b|\bcpes?\b|\bcses?\b|metal[- ]organic frameworks?|\bc?mofs?\b|covalent organic frameworks?|\bcofs?\b|segmental', s)
            if code == 'M02' and not m and re.search(r'(?:sulfur|cathode) hosts?|host materials?', s):
                if COMPOUND.search(s) or re.search(r'metal[- ]organic|\bmofs?\b|\bcofs?\b|electrides?|organic cages?|\bpoc\b|bimetallic', s):
                    m = re.search(r'(?:sulfur|cathode) hosts?|host materials?', s)
            if m and code == 'M02' and ELECTROLYTE.search(s) and not re.search(r'sulfur|sulphur|polysulfide|li2s|cathode|host|redox|conversion', s):
                m = None  # 电解质语境里的高熵/MXene/填料、合成或聚合用的催化，不是硫转化催化
            if m and code == 'M03' and position_flags(s)['负极侧'] and not re.search(r'sulfur|sulphur|cathode|polysulf|li2s|catholyte|\bo2\b|oxygen|sslob|li-o', s):
                m = None  # 负极上的氧化还原界面层/介体层不是正极介体
            if m and code == 'M03' and scope != '液态锂硫' and re.fullmatch(r'mediators?', m.group()) and not re.search(r'redox|sulfur|sulphur|polysulf|li2s|\bo2\b|oxygen', s):
                m = None  # 固态组里裸的 mediator 多为化学"介导"，不是氧化还原介体
            if m and code == 'M02' and scope == '固态锂金属' and not re.search(r'catalys|catalytic', m.group()):
                m = None  # 固态锂金属组的 MXene/高熵/异质结构多为电解质或界面材料，不是硫转化催化剂
            if m and code == 'M04' and re.search(r'te[- ]dop|tellurium|selenium[- ]doped|se[- ]doped', m.group()):
                if not re.search(r'(?:te|tellurium|se|selenium)[- ](?:co-)?dop\w* (?:[\w@/-]+ ){0,3}(?:sulfur|s|span|sulfurized|ppan|cathodes?)\b|doped sulfur|dop\w* (?:to|into|in) (?:the )?(?:sulfur|s)\b', s):
                    m = None  # 掺杂对象不是硫（如 Te 掺杂催化剂）
            if m and code == 'M07' and (re.search(r'pyroly|carboni[sz]|precursor|derived from', s) or re.search(r'conduct\w* polymer electrolyte', s)) and not re.search(r'pedot|electron\w* conduct', s):
                m = None  # 聚苯胺作碳前驱体、离子导电聚合物电解质都不算导电聚合物方法
            if code == 'M10' and not m and re.search(r'high[- ]entropy', s) and ELECTROLYTE.search(s) and not re.search(r'catalys', s):
                m = re.search(r'high[- ]entropy', s)
            if m and code == 'M10':
                if scope == '液态锂硫':
                    m = None  # 液态电解液调控归 M05
                elif re.search(r'(?:se|selenium|te|tellurium)[- ](?:co-)?doped (?:sulfur|\w*s\b)|doped sulfur|sulfur cathode', s):
                    m = None  # 掺杂对象是硫活性物（归 M04）
                elif re.match(r'n(?:ovel|ew)', m.group()) and 'polymer' in m.group():
                    m = None  # 新聚合物电解质归 M11
            if m and code == 'M05' and scope != '液态锂硫':
                if not re.search(r'solvation|solvating|coordination (?:entropy|structure|environment)|li\+ coordination|donor number|electrolyte additives?|additives? (?:in|into|to|for) (?:the )?(?:\w+ )?electrolyte|high[- ]concentration|co[- ]solvent|diluent|electrolyte (?:design|engineering|formulation|regulation)|fluorinated (?:ether|solvent)', s):
                    m = None  # 固态组里裸的 additive/solvent 多为正极添加剂或溶剂法工艺
            if m and code == 'M05' and re.search(r'(?:additive|solvent)[- ]free|free of (?:\w+ )?(?:additives?|solvents?)', s) and not re.search(r'solvation|electrolyte additive', s):
                m = None
            if m and code == 'M11':
                if scope == '液态锂硫':
                    if not re.search(r'polymer electrolyte|composite (?:solid |polymer |solid-state )?electrolyte|gel polymer|gel electrolyte', s):
                        m = None  # 液态组里的聚合物多为粘结剂/添加剂/隔膜材料
                elif re.search(r'cross|pvdf|poly ?\(|polymer matri', m.group()) and not re.search(r'electrolyte|ion conduct|ionic conduct|\b[sgc]?pes?\b|\bcses?\b', s):
                    m = None  # 交联、PVDF 等只有在电解质语境才算
            if m and code == 'M12' and re.search(r'templat\w*|morphology[- ]directing|precursor', s) and not re.search(r'electrolyte', s):
                m = None  # 聚离子液体作模板/前驱体不是含液成分
            if m and code == 'M12' and scope == '液态锂硫' and not re.search(r'ionic liquid|gel polymer|gel electrolyte|in[- ]situ polymeri|quasi[- ]solid[- ](?:state )?electrolyte|plastici', s):
                m = None  # 液态组里 DOL/DME 等是常规电解液，不算方法
            if m and code == 'M15' and m.group().startswith('encapsulat') and not re.search(r'sulfur|sulphur|\bs8\b|li2s|polysulfide', s):
                m = None
            if m and code == 'M07' and re.search(r'ion[- ]conducting polymer|ion[- ]conductive polymer', s) and not re.search(r'pedot|polypyrrole|\bppy\b|polyaniline|\bpani\b|polythiophene|electron\w* conduct', s):
                m = None  # 离子导电聚合物电解质不是导电聚合物
            if m and code == 'X01' and re.search(r'host', m.group()) and re.search(r'sulfur host|host for (?:li|lithium)[- ]?(?:s\b|sulfur|sulphur)|lithium[- ]sulfur|\bli[- ]s\b', s):
                m = None  # "sulfur host for Li-S batteries" 是硫宿主，不是锂负极宿主
            if m and code == 'X01' and re.search(r'host|current collector|prelithiat', m.group()):
                if not position_flags(s)['负极侧'] or re.search(r'li2s|lithium sulfide|sulfur|sulphur|cathode', s):
                    m = None  # 宿主/集流体/预锂化须有明确的负极语境，Li2S 宿主、正极集流体不算
            if m and code == 'M17' and re.search(r'pressure filtration|filtration|hydroly\w*|calcin\w*|anneal\w*|pyroly\w*|synthes\w* at elevated', s) and not re.search(r'stack|operat|cycl', s):
                m = None  # 工艺过程里的压力/温度不算运行条件
            if m and code == 'M16' and 'binder' in m.group() and re.search(r'free of|without|binder[- ]free|composed of|consisting of|mixture of|and binders?\b|, binders?\b', s):
                m = None
            if m:
                hits[code] = (src, s, m.group())
                break
    # 单原子论文里的"catalytic"不再重复计入金属化合物催化剂，除非另有化合物/异质结构证据
    if 'M01' in hits and 'M02' in hits:
        if not any(COMPOUND.search(s) for _, s in sents):
            del hits['M02']
    return hits


# 判位置前先去掉电池名，避免 "lithium metal batteries" 判成负极侧、"lithium-sulfur batteries" 判成正极侧
BATTERY_NAME = re.compile(
    r'(?:(?:all|quasi)[- ])?(?:solid[- ]state |polymer[- ]based |high[- ](?:voltage|energy|performance) |practical |next[- ]generation |advanced |rechargeable )*'
    r'(?:lithium|li)[- ]?(?:metal|sulfur|sulphur|s|ion|o2|oxygen|air|selenium)[- ](?:batter\w*|cells?|systems?|chemistr\w*)'
    r'|\b(?:as+|ss|qs)?l(?:m|s|i|ms|ss)?bs?\b|\blsbs?\b|\blisbs?\b|\bli[- ]s\b|lithium[- ]sulfur|sulfur batter\w*|metal batter\w*')


def position_flags(s):
    t = BATTERY_NAME.sub(' ', s)
    return {'正极侧': bool(CATHODE.search(t)), '负极侧': bool(ANODE.search(t)),
            '隔膜/中间层': bool(SEPARATOR.search(t)), '电解质': bool(ELECTROLYTE.search(t))}


def position(s):
    f = position_flags(s)
    pos = [k for k in ('正极侧', '负极侧', '隔膜/中间层') if f[k]]
    if not pos and f['电解质']: pos.append('电解质体相')
    return '+'.join(pos) or '未明确'


def only_anode(s):
    f = position_flags(s)
    return f['负极侧'] and not (f['正极侧'] or f['电解质'] or f['隔膜/中间层'])


def materials(text):
    """从原文（未小写）抽化学式/缩写，作代表材料线索；机器抽取，未核对"""
    t = re.sub(r'([A-Za-z])\s+(\d)', r'\1\2', text)
    t = re.sub(r'(\d)\s+([A-Z])', r'\1\2', t)
    out = set()
    for tok in re.findall(r'\b[A-Za-z0-9@\-–/().δ]{2,}\b', t):
        tok = tok.strip('()-–/.')
        tok = re.sub(r'-(?:based|type|rich|free|derived|modified|coated|doped|containing|integrated|enabled)$', '', tok, flags=re.I)
        tok = re.sub(r'(\d)([A-Z][a-z]{3,}\w*)$', r'\1', tok)  # "NCM622Cathodes" -> "NCM622"
        letters = [ch for ch in tok if ch.isalpha()]
        if re.fullmatch(r'(?:[A-Z][a-z]?\d*(?:\.\d+)?){2,}[A-Za-z0-9.]*', tok) and re.search(r'\d', tok):
            out.add(tok)
        elif re.fullmatch(r'[A-Z][A-Za-z0-9\-@]{2,}', tok) and tok.upper() not in GENERIC and (
                tok.lower() in ('mxene', 'mxenes') or (letters and sum(ch.isupper() for ch in letters) / len(letters) >= 0.6)):
            out.add(tok)
    return out


GENERIC = set('''LSB LSBS LSBSS ASSLSB ASSLSBS ASSLB ASSLBS SSLSB SSLSBS SSLMB SSLMBS SSB SSBS SSE SSES SPE SPES CPE CPES CSE CSES
LMB LMBS LIB LIBS LMA LMAS LRR DFT XRD XPS TEM SEM EIS CV GITT NMR FTIR ToF-SIMS TOF-SIMS SEI CEI SRR SOR LPS LIPS LIPSS LPSS PSS
EV MV CE DOD ICE SOC AFM HRTEM XAS XANES EXAFS STEM MD AIMD CCD RT HT ESW ESR IL ILS GPE GPES QSSE LI-S AND THE FOR WITH'''.split())


def main():
    corpus, tags = load_corpus(), load_tags()
    scopes = scope_papers(corpus, tags)
    p03_phrase = {}
    with open(SRC / '逐篇主题与证据.csv', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r['标签号'] == 'P03':
                p03_phrase[r['编号']] = (r['命中短语'], r['摘要证据句_规范化'])

    rows, na_rows, unclassified, na_papers = [], [], [], []
    for scope, papers in scopes.items():
        for r in papers:
            full = norm(r['title'] + ' ' + r['abstract'])
            # 不适用规则 3：动力学命中实为锂沉积动力学，且通篇不涉及硫转化
            if scope in ('液态锂硫', '固态锂硫') and r['id'] in p03_phrase:
                ph, s = p03_phrase[r['id']]
                if LIQUID_ANODE_KINETICS.search(ph) and not SULFUR_CONV.search(full.replace(ph, '')):
                    na_papers.append({'范围': scope, '编号': r['id'], '年份': r['year'], 'DOI': r['doi'], '标题': r['title'],
                                      '不适用原因': '动力学命中为锂沉积/剥离动力学，摘要不涉及硫转化', '命中短语': ph, '原句': s})
                    continue
            if scope != '固态锂金属':
                why = None
                if re.search(r'sodium|\bna[- ](?:s|ion|metal)\b|potassium|\bk[- ]s\b|magnesium|\bmg[- ]s\b|alumin\w*[- ]sulfur|\bal[- ]s\b|calcium', full) and not re.search(r'lithium|\bli[- ]s\b|\bli\b|li2s|\blsbs?\b', full):
                    why = '非锂硫体系（钠/钾/镁/铝/钙）'
                elif not re.search(r'sulfur|sulphur|polysulfide|li2s|\bs8\b|\bli[- ]s\b|\blsbs?\b|lithium[- ]sulfur|\bs[- ]p ?2 ?s ?5|\bs/c\b|\bs@', full):
                    why = '摘要不涉及硫或锂硫（多为电解质材料或锂负极研究）'
                if why:
                    na_papers.append({'范围': scope, '编号': r['id'], '年份': r['year'], 'DOI': r['doi'], '标题': r['title'],
                                      '不适用原因': why, '命中短语': '', '原句': norm(r['abstract'])[:300]})
                    continue
            own = own_sentences(r['abstract'])
            sents = [('标题', norm(r['title']))] + [('做法句', s) for s in own]
            hits = match_classes(sents, scope)
            mats = materials(r['title'] + ' ' + ' '.join(own))
            if not [c for c in hits if c != 'X01']:
                unclassified.append({'范围': scope, '编号': r['id'], '年份': r['year'], 'DOI': r['doi'], '标题': r['title'],
                                     '做法句': ' | '.join(own)[:1500], '只命中负极专用': 'X01' in hits})
            for code, (src, s, ph) in hits.items():
                cause, name = next((c, n) for k, c, n, _ in VOCAB if k == code)
                pos = position(s)
                row = {'范围': scope, '编号': r['id'], '年份': r['year'], 'DOI': r['doi'], '标题': r['title'],
                       '原因': cause, '类别编号': code, '方法类别': name, '作用位置（按命中句）': pos,
                       '命中短语': ph, '证据来源': src, '原句（规范化）': s,
                       '原句回查': '✅' if s in norm(r['title']) or s in norm(r['abstract']) else '❌',
                       '材料线索（机器抽取）': '、'.join(sorted(mats))[:300]}
                # 不适用规则 1：锂负极专用方法；规则 2：界面层/包覆层只在锂负极
                if code == 'X01':
                    row['不适用原因'] = '锂负极专用方法，与硫正极转化无关'
                    na_rows.append(row)
                elif code in ('M15', 'M08') and position_flags(s)['负极侧'] and not position_flags(s)['正极侧']:
                    row['不适用原因'] = '界面层/包覆层/混合导体层作用在锂负极（命中句讲负极、未涉及正极）'
                    na_rows.append(row)
                elif only_anode(s):
                    row['不适用原因'] = '命中句只讲锂负极（无正极、电解质或隔膜语境）'
                    na_rows.append(row)
                else:
                    rows.append(row)
    json.dump({'rows': rows, 'na_rows': na_rows, 'na_papers': na_papers, 'unclassified': unclassified,
               'scope_n': {k: len(v) for k, v in scopes.items()}},
              open(OUT / '_inventory.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print('范围篇数', {k: len(v) for k, v in scopes.items()})
    print('适用行', len(rows), '不适用行', len(na_rows), '不适用论文', len(na_papers), '未归类论文', len(unclassified))
    print('原句回查 ❌ 数', sum(r['原句回查'] == '❌' for r in rows + na_rows))
    c = collections.Counter((r['范围'], r['类别编号']) for r in rows)
    for code, cause, name, _ in VOCAB[:-1]:
        print(f"{code} {name[:24]:<26}", '  '.join(f"{s[:5]}:{c[(s, code)]:>4}" for s in scopes))
    print('未归类按范围', collections.Counter(u['范围'] for u in unclassified))
    print('不适用行按范围/规则', collections.Counter((r['范围'], r['不适用原因'][:6]) for r in na_rows))


if __name__ == '__main__':
    main()
