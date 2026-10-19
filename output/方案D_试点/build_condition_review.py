import csv
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).parent
TEXTS = ROOT / '候选问题筛选' / '全文文本'
papers = {r['编号']: r for r in csv.DictReader((ROOT.parent / 'dataset_v2' / '论文表.csv').open(encoding='utf-8-sig'))}

def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', s).replace('\u00ad','')).strip()

# Deliberately short source passages. Page numbers are located from the saved
# full text rather than inferred from article page ranges.
evidence = [
 ('W7128180073','polymer binders within the cathode composite to better maintain electrode integrity','作者已提出加入聚合物维持完整性的方向；不能把“加聚合物”本身声称为新概念。'),
 ('W7128180073','After 40 cycles, 4.8 mAh cm−2','5 mg硫/cm²的容量衰减是实际待解决问题。'),
 ('W7128180073','under 81 MPa external pressure','运行堆压是81 MPa。'),
 ('W7128180073','carbon composite, Super P, and SE (4:1:5 weight ratio)','结合S:KB=3:1，推得总正极名义质量比S:KB:Super P:SE=30:10:10:50。'),
 ('W7130661640','the optimized pressure of 80 MPa','高载量梯度正极的运行压力。'),
 ('W7130661640','high areal capacities of 7.20 and 9.02 mAh cm−2','25°C和45°C的11.4 mg硫/cm²结果；勿和其他温度混排。'),
 ('W4415543410','at 50 MPa (testing pressure)','2025梯度正极的测试压力。'),
 ('W4415543410','weight ratios of x:(85-x):15','电解质:硫:PPCF配比随层改变，平均硫占比40%。'),
 ('W7139977491','15 wt% sulfur (S8) and 15 wt% tungsten sulfide (WS2)','低压杂化正极中的单质硫仅15 wt%。'),
 ('W7139977491','approximately 1.13 mg cm−2','这里指总正极活性物载量，不是单质硫载量。'),
 ('W7139977491','low pressure (~0.3 MPa)','低压性能已有人验证，不能把所有低压方案视为空白。'),
 ('W4393342138','Li7P3S11 (LPS) electrolyte','原始论文的电解质为Li7P3S11，不能写成Li6PS5Cl。'),
 ('W4393342138','Even after 250 cycles, A19P5 maintained a specific capacity of 715 mAh g−1','4.5 mg硫/cm²、30°C、250圈容量；有明确高载量长循环参照。'),
 ('W7166647466','49:21:30 (S:C:SSE).','复合正极质量配比为S:C:SSE=49:21:30。'),
 ('W7166647466','of 50 MPa','宿主研究使用50 MPa堆压。'),
 ('W7169438107','All batteries tests were conducted under a pressure of 1500 kg','原文以kg记载载荷；未经校准不能当作1500 MPa或低压。'),
 ('W7169438107','mass ratio of 57:38:5','高硫含量正极：预制S/Co碳复合物:LPSC:KB。'),
 ('W4406704722','resulting in a Li2S loading of 0.11–0.14 mg cm−2','原文载量与同页3–4mg正极、25%Li2S、6mm模具的算术不一致；待原PDF/SI复核。'),
 ('W4406704722','a consistent densification pressure of 370 MPa','结果段370 MPa与方法段350 MPa相矛盾；不自行修正。'),
 ('W7162501480','cycling was initiated at an operating pressure of 125 MPa','5 MPa长循环是在高压激活、逐级降压后获得。'),
 ('W7162501480','capacity retention of 33.3% by the third cycle','直接5 MPa启动的结果明显较差。'),
 ('W7162501480','the binder content in the electrolyte was raised to 10 wt.%','增加粘结剂改善接触，同时损害电导与绝对容量，存在真实配比取舍。'),
 ('W7165555257','Using an FeS2 positive electrode and a prelithiated Si negative electrode','FeS2/预锂化硅属于边界参照，不并入S8/Li2S正极的直接性能排名。'),
]
found = []
for pid, quote, meaning in evidence:
    parts = re.split(r'=== 第 (\d+) 页 ===', (TEXTS / (pid+'.txt')).read_text(encoding='utf-8'))
    hits = [(int(parts[i]), parts[i+1]) for i in range(1,len(parts),2) if norm(quote) in norm(parts[i+1])]
    # Some extraction introduces a discretionary hyphen at a line break.
    if not hits:
        q = norm(quote).replace('−','-').replace('–','-')
        hits = [(int(parts[i]),parts[i+1]) for i in range(1,len(parts),2) if q in norm(parts[i+1]).replace('−','-').replace('–','-')]
    if not hits:
        raise ValueError(f'Quote not found: {pid} {quote}')
    found.append({'编号':pid,'页码':hits[0][0],'原文短句':quote,'用于支持的判断':meaning,'DOI':papers[pid]['DOI']})

headers = ['编号','方案与体系','配方或材料','硫载量 (mg/cm²)','其他载量口径','温度 (°C)','运行压力 (MPa)','压力历史','倍率/电压','结果与归一化口径','对照与可用判断','缺项或边界','正文页码','DOI']
rows = [
 ['W7128180073','含碘氧化还原活性正极电解质','Li10.5−xSi1.5P1.5S12−xIx，x=0/0.2/0.4；S:KB:Super P:SE名义30:10:10:50',5,'单质硫；容量包含电解质贡献',45,81,'高压运行；不是低压证明','0.1C；0.4–2.5 V vs In/InLi','初始放电9.7 mAh/cm²，40圈4.8 mAh/cm²','有x=0对照和无硫电极；反应快但高载量长期完整性仍不足','x=0也可能反应；E1为名义多相电解质；不能把总容量全算硫','9–10、12–13',''],
 ['W7130661640','离子/电子双梯度正极','Li5.5PS4.5Cl1.5:S:SWCNT=65:30:5 / 60:30:10 / 55:30:15；均匀组60:30:10',11.4,'单质硫',25,80,'全程80 MPa','0.9–2.4 V vs Li-In；文中高载量系列0.1C','25°C时7.20 mAh/cm²；45°C为9.02 mAh/cm²','有同平均配方、反向梯度、乱序及单梯度对照','梯度本身已有充分先例；不能称新策略；25°C数值与循环寿命须按图S21对应','3、7–9',''],
 ['W4415543410','梯度电解质含量+中子成像','Li5.4PS4.4Cl1.6:S:PPCF=x:(85−x):15；3层x=50/45/40',4.5,'另测6与7.5 mg硫/cm²；平均硫40 wt%',25,50,'测试堆压50 MPa；成形400 MPa','倍率C/20至C/2','梯度改善锂通量与高载量倍率性能','均匀/反向/多层对照；提供空间分布证据','50 MPa电化学测试与10 MPa成像装置条件不同，不串用','4、7–10',''],
 ['W7139977491','WS2双重氧化还原介体杂化正极','S:WS2:MWCNT:Li6PS5Cl=15:15:20:50（按方法推导）',None,'原文约1.13 mg/cm²为S+WS2总活性物；S仅占总正极15 wt%',25,0.3,'约0.3 MPa纽扣电池运行；压制压力另计','0.1–3.0 V vs Li-In','50圈831 mAh/g、保持率约83%；无WS2组371、34%','低压策略有直接证据；WS2还贡献质量与电化学作用','容量质量基准须继续核图/SI；不能将1.13当单质硫载量','1–2',''],
 ['W4393342138','弹性导电网络','S:Li7P3S11:AB:PPy@NCNT=38:38:19:5；对照38:38:24:0',4.5,'单质硫',30,None,'正文未核定绝对运行堆压；压力变化不是外压设定值','0.1C活化后0.2C','初始约6.1 mAh/cm²；250圈715 mAh/gS，对照398','同总添加剂质量对照；裸NCNT组可辨包覆作用','不能据11%应力变化宣称可在低外压运行；电位窗口与压制条件需SI','3–5、9–11',''],
 ['W7166647466','微米级微孔碳宿主','S:C:Li7P2S8Br0.5I0.5=49:21:30；YP-80F对比BP-2000/KB/CMK-3',6,'高载量系列；室温长循环另为1.5 mg硫/cm²',60,50,'恒间隙，初始设50 MPa；压制700 MPa','0.05C活化；高载量0.2–1C；0.7–2.5 V vs Li-In','6 mg硫/cm²可达约9 mAh/cm²','孔径与颗粒尺度分开；强调加工后形貌/硫迁移','不可把60°C高载量指标和22°C低载量寿命拼接','3–4、7、10–11',''],
 ['W7169438107','催化剂尺度与电解质分解取舍','Co簇约0.54 nm；高硫正极S/Co碳复合物:LPSC:KB=57:38:5；预复合S:宿主=4:1',6,'名义45 wt%硫',30,None,'原文运行载荷1500 kg；10 mm模具；未作为标定MPa采用','0.05C起始后0.1C','70圈面容量>3.51 mAh/cm²','小簇催化强也会促分解；中等簇及孔内布置提供选择性','不能把超过硫理论比容量当纯硫利用；载荷单位待核','4–5、9–11',''],
 ['W4406704722','堆压依赖的直接实验','Li2S:KB:Li6PS5Cl=25:25:50',None,'原文Li2S 0.11–0.14 mg/cm²，但与质量/直径计算不一致',None,None,'1.8/3.5/7.1/10.6 MPa分别维持；制片350与370 MPa自相矛盾','0.1C；0.58–2.68 V vs Li-In','100圈保持率6%/61%/78%/74%','配方相同，压力下降伴随失活与界面阻抗增加','载量和制片压力须核原PDF/SI；暂不用它给高载量结论','2–4',''],
 ['W7162501480','SEBS复合电解质层','Li5.5PS4.5ClBr0.5+SEBS；10/20 wt%额外测试；基准比例待SI',None,'5 MPa长循环对应载量尚未核定；不得挪用其他图3.53 mg/cm²',None,5,'125→100→75→50→25→12.5→5 MPa','室温；0.0–3.0 V vs Li-In','降压后5 MPa循环300圈保持率78%','与纯无机层比较；柔性/粘结改善接触但电导下降','预活化历史必要；室温原文未给精确温度数值','7–10',''],
 ['W7162501480','同体系直接低压启动','同上',None,'同一论文的另一测试；载量待核',None,5,'直接5 MPa启动','其余工况须按图S26复核','初始548.6 mAh/g；第3圈保持率33.3%','证明“降压后能循环”与“低压直接启动”不同','不与上一行直接做数值效应量，尚未核齐载量/倍率','7',''],
 ['W7165555257','FeS2/预锂化硅应变协调（边界）','FeS2正极+Li2Si负极；Li5.5PS4.5Cl1.5',None,'FeS2质量不是单质硫载量',None,15,'降压工况；高面容量21.7 mAh/cm²在100 MPa','见原文不同工况','15 MPa报告868.4 mAh/g；高面容量与超长循环不能全部归15 MPa','全电池应变补偿可作方法启示','正负极同时变，不能证明S8正极材料或界面层有效','1–3',''],
]
for row in rows: row[-1] = papers[row[0]]['DOI']

recipe_headers = ['组别','用途','电解质(正极内)','S (wt%)','KB (wt%)','Super P (wt%)','PPy@NCNT (wt%)','裸NCNT (wt%)','正极内电解质 (wt%)','依据与状态']
recipes = [
 ['R00','原配方基准','E0',30,10,10,0,0,50,'S/KB=3:1与(S/KB):SuperP:SE=4:1:5推导；已报道配比'],
 ['R10','仅改变电解质','E1',30,10,10,0,0,50,'已报道配比；统一隔层后是改造参照，不称原文整电池复现'],
 ['R01','仅引入弹性网络','E0',30,10,5,5,0,50,'本轮提出的组合；5 wt%参考另一篇Li7P3S11工作，兼容性尚未证实'],
 ['R11','组合候选','E1',30,10,5,5,0,50,'本轮提出；检验电解质功能与接触网络是否互相促进或抵消'],
 ['R1N','裸管机制对照','E1',30,10,5,0,5,50,'仅在R11有收益时增加；区分管状电子网络与PPy包覆效应'],
]
source_ids = ['W1989121075','W7167612024','W2294978050','W7165620135','W7162652379']
source_records = [{k:papers[i][k] for k in ['编号','年份','标题','摘要','DOI','分组']} for i in source_ids]

# An explicit local combined-term query, including variants, is a novelty lead
# only. Lack of a hit does not establish novelty.
target = [r for r in papers.values() if r['分组']=='固态锂硫']
cohits=[]
for r in target:
    t=r['标题']+' '+r['摘要']
    if re.search(r'polypyrrole|\bPPy\b',t,re.I) and re.search(r'iodine|iodide|Li10[. ]|redox.active catholyte',t,re.I): cohit=r['编号']; cohits.append(cohit)
data={'headers':headers,'rows':rows,'recipe_headers':recipe_headers,'recipes':recipes,'evidence':found,'sources':source_records,'local_combo_query':{'searched_records':len(target),'abstracts':sum(bool(r['摘要'].strip()) for r in target),'hits':cohits},'reviewed_papers':len(set(r[0] for r in rows))}
(ROOT/'_index_builder'/'condition_review_data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

lines=['# 全文条件核查依据','', '> 2026-10-19。本轮定向核读10篇原始研究的条件/机制段落（9篇S8/Li2S直接证据，1篇FeS2边界参照）；并非10篇全部逐字通读。与原F专项有重合，不能直接相加。页码为本地全文页码标记。引句仅做空白、Unicode兼容字符及软连字符规范化后定位，不改变科学含义。','']
for e in found:
    lines += [f"## {e['编号']}，p.{e['页码']}",f"[{papers[e['编号']]['标题']}](https://doi.org/{e['DOI']})",'',f"> {e['原文短句']}",'',e['用于支持的判断'],'']
lines += ['## 有限查新记录','',f"本地主库1,181条题名/可用摘要中，(polypyrrole或PPy) 与 (iodine、iodide、Li10或redox-active catholyte) 同现记录：{cohits or '0条'}。",'2026-10-19网页检索了精确名义式+polypyrrole、iodine+polypyrrole+all-solid-state+sulfur、redox-active catholytes+carbon nanotube、Li10.1+PPy+sulfur。所返结果未核实到本次具体配方，但这不是完整新颖性检索，也不涵盖无摘要、补充材料与专利。','已有E1原论文已建议聚合物维持正极完整性。因此潜在贡献需落在具体相/配比/加工/性能交互作用及可证伪机制上。']
(ROOT/'全文条件核查依据.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'reviewed_papers':data['reviewed_papers'],'condition_rows':len(rows),'verified_excerpts':len(found),'combo_hits':cohits},ensure_ascii=False))
