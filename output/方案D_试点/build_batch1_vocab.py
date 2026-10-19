"""方案D §9.1 词表试点·批1：Claude 开放抽取结果 → 代码核对原文短语 → 输出 Excel（停点 1 给用户看）。

用法：python build_batch1_vocab.py <摘要样本_三批.csv> <论文表.csv> <输出.xlsx>
"""
import re
import sys
import unicodedata
import pandas as pd
from openpyxl.utils import get_column_letter

# ---------------- 词表初稿 v0（由批1 开放抽取归纳） ----------------
PROBLEMS = [
    ('P01', '枝晶 / 穿透', '锂枝晶生长、穿透电解质或短路'),
    ('P02', '界面副反应 / 化学不相容', '电解质被还原或氧化、与电极或多硫化物反应、SEI 不受控、负极腐蚀'),
    ('P03', '界面接触差 / 界面电阻', '界面离子传输受限、接触丧失、空洞裂纹、粉化、界面电阻高'),
    ('P04', '离子传输不足', '离子电导率低、迁移数低、离子通路不连续（位置决定是电解质还是正极里的）'),
    ('P05', '电子传导不足', '硫、Li₂S 或电极绝缘，电子通路不足'),
    ('P06', '电化学窗口窄 / 电解质分解', '电解质在工作电位下分解、窗口不够'),
    ('P07', '空气 / 湿度不稳定', '与水或空气反应、表面杂质（Li₂CO₃、LiOH）'),
    ('P08', '力学问题', '脆性、强度不足、硬脆材料需要高堆压'),
    ('P09', '相稳定性 / 杂相 / 纯度', '相变、杂相、合成残留'),
    ('P10', '多硫化物溶解与穿梭', '多硫化物溶解、迁移、硫流失'),
    ('P11', '转化动力学慢', '硫—Li₂S 转化慢、Li₂S 难分解、过电位大'),
    ('P12', '体积与形貌变化', '体积膨胀、电极形貌变粗糙'),
    ('P13', '活性物利用率低 / 厚电极受限', '硫利用率低、高载量厚电极传输受阻'),
    ('P14', '电池级能量密度低', '电解质层厚、电解液过量等导致整电池能量密度低'),
    ('P15', '安全 / 易燃', '有机电解液易燃'),
    ('P16', '成本 / 规模化 / 加工', '成本、规模化制备、加工难（含填料分散）'),
    ('P17', '知识或方法空白（待定）', '机理不清、设计原则缺乏、预测方法不准；不是电池里的物理问题'),
    ('P99', '其他 / 新问题 / 不确定', '归不进以上各类'),
    ('不计', '性能症状', '容量衰减、寿命短等结果描述，不作问题标签，只记具体原因'),
]
STRATEGIES = [
    ('S01', '换主体材料 / 新电解质体系', '新电解质、新溶剂、新聚合物主体、改用固态电解质'),
    ('S02', '掺杂、取代或缺陷工程', '元素取代、掺杂、引入空位'),
    ('S03', '填料、增塑剂或复合增强', '电解质中加入无机/有机填料、增塑剂、增强骨架'),
    ('S04', '聚合物结构设计', '交联、互穿、梳状、链构象调控'),
    ('S05', '包覆', '颗粒或电极表面包覆'),
    ('S06', '中间层 / 人工界面层', '中间层、人工 SEI、ALD 薄层、隔开两相的保护层'),
    ('S07', '隔膜修饰', '隔膜涂层、功能隔膜'),
    ('S08', '导电骨架 / 宿主结构', '碳网络、3D 框架、自支撑电极、集流体结构'),
    ('S09', '催化剂或氧化还原促进剂', '电催化剂、单原子、氧化还原加速'),
    ('S10', '极性吸附 / 锚定材料', '吸附或锚定多硫化物的材料（含计算筛选）'),
    ('S11', '粘结剂', '功能粘结剂'),
    ('S12', '负极结构或合金设计', '复合锂负极、合金负极、负极集流体'),
    ('S13', '合成与加工工艺', '合成路线、球磨、退火、表面清洁、沉积条件、预锂化'),
    ('S14', '运行条件', '运行温度、压力'),
    ('S15', '电池结构设计', '薄电解质、正极支撑、软包设计'),
    ('S16', '复合正极配比与微结构', '正极中活性物/电解质/碳的配比与分布'),
    ('S17', '计算筛选 / 预测方法（待定）', '方法本身，不是电池里实施的策略'),
    ('S99', '其他 / 不确定', '笼统或归不进以上各类'),
]

# ---------------- 论文级核查（批1 全部 60 篇） ----------------
# 序号, 组别核查, 建议归属, 理由, 文献类型, 液相状态, 负极类型, 实验配置, 纯电解质研究
PAPERS = [
    (1, '符合', '固态锂硫', '综述，兼论锂空气', '综述', '全固态', '未写明', '不适用', '否'),
    (2, '存疑', '非硫固态', '只做锂对称电池，锂硫只是展望', '原创', '全固态', '锂金属', '对称电池', '是（仅对称电池）'),
    (3, '符合', '固态锂硫', '', '原创（机理/表征）', '全固态', '未写明', '材料测试', '否'),
    (4, '存疑', '液态锂硫', '没提固态，讲多硫化物经隔膜穿梭；旧标签"硼氢化物"来自还原剂硼氢化钠', '原创', '液态（推断）', '未写明', '未写明', '否'),
    (5, '存疑', '液态锂硫', '凝胶聚合物只作中间层捕获多硫化物', '原创', '含液或凝胶', '未写明', '全电池', '否'),
    (6, '符合', '固态锂硫', '聚合物电解质 50 °C 运行，多硫化物会溶入聚合物', '原创', '全固态', '锂金属', '全电池', '否'),
    (7, '存疑', '液态锂硫', '锂硫电池用醚类/碳酸酯电解液，固态电解质只作负极填料', '原创', '液态', '锂金属', '半电池；全电池', '否'),
    (8, '符合', '固态锂硫', '', '原创（原位表征）', '全固态', '未写明', '材料测试', '否'),
    (9, '存疑', '状态待核实', '混合电解质，含液', '原创', '含液或凝胶', '锂金属', '未写明', '否'),
    (10, '符合', '固态锂硫', '', '原创', '全固态', '锂金属', '全电池', '否'),
    (11, '符合', '固态锂硫', '', '原创', '全固态', '锂金属', '对称电池；全电池', '否'),
    (12, '符合', '固态锂硫', '', '原创', '全固态', '锂金属', '全电池', '否'),
    (13, '不属于', '不属于', '意大利储能政策研究', '综述（政策）', '不适用', '不适用', '不适用', '否'),
    (14, '符合', '固态锂硫', '综述，含钠/锌/镁硫', '综述', '全固态', '未写明', '不适用', '否'),
    (15, '存疑', '液态锂硫', '高载量液态锂硫综述，固态只在展望里', '综述', '液态', '未写明', '不适用', '否'),
    (16, '存疑', '液态锂硫', '隔膜修饰，多硫化物溶于电解液；旧标签"氧化物"来自 LLTO 涂层', '原创', '液态', '锂金属', '全电池', '否'),
    (17, '存疑', '液态锂硫', 'Li₃PS₄ 只作锂负极人工 SEI，电池为液态', '原创', '液态（推断）', '锂金属', '对称电池；全电池', '否'),
    (18, '符合', '固态锂硫', '', '原创（机理）', '全固态', '未写明', '全电池；材料测试', '否'),
    (19, '符合', '固态锂硫', '摘要开头被截断', '原创', '全固态', '锂金属', '对称电池；全电池', '否'),
    (20, '符合', '固态锂硫', '综述', '综述', '全固态', '锂金属', '不适用', '否'),
    (21, '符合', '液态锂硫', '', '原创', '液态', '未写明', '未写明', '否'),
    (22, '符合', '液态锂硫', '研究硫浓度这一参数', '原创', '液态', '未写明', '未写明', '否'),
    (23, '符合', '液态锂硫', '', '原创（原位表征）', '液态', '未写明', '材料测试', '否'),
    (24, '符合', '液态锂硫', '', '计算', '液态', '不适用', '不适用', '否'),
    (25, '符合', '液态锂硫', '', '原创', '液态', '未写明', '全电池', '否'),
    (26, '符合', '液态锂硫', '综述', '综述', '液态', '未写明', '不适用', '否'),
    (27, '不属于', '不属于', '超级电容器；旧标签 SPAN 来自"硫化聚丙烯腈"前驱体', '原创', '不适用', '不适用', '不适用', '否'),
    (28, '符合', '液态锂硫', '', '原创', '液态', '未写明', '全电池', '否'),
    (29, '符合', '液态锂硫', '', '原创', '液态', '锂金属', '全电池', '否'),
    (30, '符合', '液态锂硫', '', '原创', '液态', '未写明', '全电池（含软包）', '否'),
    (31, '符合', '液态锂硫', '', '原创', '液态', '未写明', '全电池', '否'),
    (32, '符合', '液态锂硫', '', '原创', '液态', '未写明', '全电池', '否'),
    (33, '符合', '液态锂硫', '', '原创', '液态', '未写明', '全电池', '否'),
    (34, '符合', '液态锂硫', '', '原创', '液态', '未写明', '全电池（软包）', '否'),
    (35, '符合', '液态锂硫', '', '计算', '液态', '不适用', '不适用', '否'),
    (36, '存疑', '液态锂硫（多体系综述）', '生物质碳综述，覆盖锂离子/锂硫/钠/钾', '综述', '液态', '不适用', '不适用', '否'),
    (37, '符合', '液态锂硫', '', '原创', '液态', '未写明', '全电池', '否'),
    (38, '符合', '液态锂硫', '', '计算', '液态', '不适用', '不适用', '否'),
    (39, '符合', '液态锂硫', '', '原创', '液态', '未写明', '全电池', '否'),
    (40, '不属于', '不属于', '二价离子电池 MXene 综述', '综述', '不适用', '不适用', '不适用', '否'),
    (41, '不属于', '不属于', '水系锂电池；旧标签"凝胶"来自负极保护层', '原创', '液态（水系）', '锂金属', '全电池', '否'),
    (42, '存疑', '状态待核实', '含 EC/PC 增塑剂', '原创', '含液或凝胶', '不适用', '材料测试', '是'),
    (43, '符合', '非硫固态', '薄膜电池正极', '原创', '全固态', '未写明', '材料测试', '否'),
    (44, '符合', '非硫固态', '', '原创（结构）', '全固态', '不适用', '材料测试', '是'),
    (45, '存疑', '非硫固态（多器件综述）', '还涉及燃料电池、驱动器；含离子液体', '综述', '含液或凝胶', '不适用', '不适用', '是'),
    (46, '存疑', '状态待核实', '准固态，新边界不纳入', '原创', '含液或凝胶', '锂金属', '对称电池；半电池', '是'),
    (47, '存疑', '状态待核实', '含四甘醇二甲醚', '原创', '待核实', '锂金属', '全电池', '否'),
    (48, '符合', '非硫固态', '', '原创', '全固态', '未写明', '全电池', '否'),
    (49, '符合', '非硫固态', '', '原创', '全固态', '锂金属', '对称电池；全电池', '否'),
    (50, '符合', '非硫固态', '', '原创', '全固态', '未写明', '全电池', '否'),
    (51, '符合', '非硫固态', '综述', '综述', '全固态', '不适用', '不适用', '是'),
    (52, '存疑', '状态待核实', '凝胶聚合物电解质，新边界不纳入', '原创', '含液或凝胶', '锂金属', '对称电池；全电池', '否'),
    (53, '符合', '非硫固态', '', '原创', '全固态', '不适用', '材料测试', '是'),
    (54, '符合', '非硫固态', '', '原创', '全固态', '锂金属', '对称电池；全电池', '否'),
    (55, '符合', '非硫固态', '', '原创', '全固态', '锂合金', '全电池', '否'),
    (56, '符合', '非硫固态', '', '原创', '全固态', '不适用', '材料测试', '是'),
    (57, '存疑', '非硫固态（钠、锂兼论）', '以钠 NASICON 为主的综述', '综述', '全固态', '锂金属', '不适用', '否'),
    (58, '符合', '非硫固态', '', '计算', '全固态', '不适用', '不适用', '是'),
    (59, '存疑', '非硫固态（方法论文）', '比较 EIS 与恒流法，聚合物电解质只是例子', '方法', '全固态', '锂金属', '对称电池；半电池', '否'),
    (60, '符合', '非硫固态', '', '原创', '全固态', '锂金属', '全电池', '否'),
]

# ---------------- 开放抽取（原始标注，不去重） ----------------
# 序号, 类型, 开放描述, 词表标签, 角色, 位置, 具体物质, 针对的问题, 声称作用, 原文短语
ITEMS = [
    (1, '问题', '有机电解液易燃', 'P15', '背景提及', '电池整体', '', '', '', 'flammability of their organic electrolytes'),
    (1, '问题', '多硫化物穿梭', 'P10', '背景提及', '正极内部', '', '', '', 'shuttle effect'),
    (1, '策略', '改用固态电解质', 'S01', '背景提及', '电解质本体', '固态电解质', 'P15；P10', '', 'The use of solid‐state Li–air and Li–S batteries is one of the best solutions'),
    (1, '问题', '固态电解质离子电导', 'P04', '研究对象', '电解质本体', '', '', '', 'ionic conductivities and chemical stabilities'),
    (1, '问题', '固态电解质化学稳定性（对象不明）', 'P99', '研究对象', '电解质本体', '', '', '', 'ionic conductivities and chemical stabilities'),
    (1, '策略', '复合正极优化', 'S16', '背景提及', '正极内部', '', '', '', 'optimization of composite cathodes'),
    (1, '策略', '电极-电解质界面修饰', 'S06', '背景提及', '未明确', '', '', '', 'modification of the electrode–electrolyte interface'),
    (2, '问题', '锂枝晶', 'P01', '研究对象', '负极侧', '', '', '', 'effectively block dendrites'),
    (2, '策略', '3D LLZO 陶瓷纳米纤维网络复合进 PEO', 'S03', '本文实施', '电解质本体', 'Li6.4La3Zr2Al0.2O12 纳米纤维；PEO', '未明确', '连续 Li⁺ 通道；增强力学；阻挡枝晶', '3D lithium-ion-conducting ceramic network based on garnet-type Li6.4La3Zr2Al0.2O12 (LLZO)'),
    (3, '问题', '电极间经电解质的离子传输差', 'P04', '背景提及', '电解质本体', '', '', '', 'poor Li-ion transport between the electrodes via the electrolyte'),
    (3, '问题', 'Li6PS5Cl–Li2S 界面离子传输受限', 'P03', '研究对象', '正极-电解质界面', '', '', '', 'The limited Li-ion transport over the Li6PS5Cl-Li2S interface'),
    (4, '问题', '多硫化物穿梭', 'P10', '背景提及', '正极内部', '', '', '', 'polysulfide-shuttle effect at the cathode'),
    (4, '策略', '导电石墨烯网络作硫纳米颗粒骨架', 'S08', '本文实施', '正极内部', '还原氧化石墨烯；硫纳米颗粒', 'P10', '更好地固定硫物种', 'A conductive nanostructured graphene network is a suitable candidate that can serve as a scaffold for holding sulfur nanoparticles'),
    (4, '策略', '硫代硫酸钠酸化制硫纳米颗粒', 'S13', '本文实施', '正极内部', '硫代硫酸钠', '未明确', '电化学表现更好', 'the acidification of sodium thiosulfate from alkaline media into sulfur nanoparticles'),
    (5, '问题', '硫绝缘', 'P05', '背景提及', '正极内部', '', '', '', 'overcome the insulating nature and volume expansion of S'),
    (5, '问题', '硫体积膨胀', 'P12', '背景提及', '正极内部', '', '', '', 'overcome the insulating nature and volume expansion of S'),
    (5, '策略', 'CNF 网络作集流体和硫载体', 'S08', '本文实施', '正极内部', '碳纳米纤维', 'P05；P12', '', 'The CNF network is used as the current collector and S holder'),
    (5, '策略', 'PVDF-HFP/CNF 复合中间层', 'S06', '本文实施', '隔膜或中间层（待定）', 'PVDF-HFP；碳纳米纤维', '未明确', '捕获多硫化物、回收硫', 'used as an interlayer to trap polysulfides'),
    (6, '问题', '液态电解液易燃', 'P15', '背景提及', '电池整体', '', '', '', 'flammable liquid solutions'),
    (6, '策略', 'PEGDME 基复合聚合物电解质', 'S01', '本文实施', '电解质本体', 'PEGDME；陶瓷；锂盐', 'P15', '热稳定、低界面电阻、快 Li⁺ 传输', 'composite polymer electrolyte based on a poly(ethylene glycol) dimethyl ether (PEGDME)'),
    (6, '策略', '中温运行实现类液态转化', 'S14', '本文实施', '电池整体', '', '未明确', '类液态 Li–S 转化', 'by heating at moderately high temperature'),
    (7, '问题', '锂粉化与电接触丧失', 'P03', '研究对象', '负极侧', '', '', '', 'lithium pulverization and associated loss of electrical contact'),
    (7, '问题', '锂枝晶', 'P01', '研究对象', '负极侧', '', '', '', 'the lithium dendrite growth'),
    (7, '策略', '固态电解质纳米颗粒作锂负极保形/牺牲填料', 'S12', '本文实施', '负极侧', '固态电解质纳米颗粒；Cu 箔', 'P03；P01', '引导锂成核、无枝晶', 'solid‐state electrolyte (SSE) nanoparticles as conformal/sacrificial fillers'),
    (7, '策略', '嵌入 Cu 集流体', 'S12', '本文实施', '负极侧', 'Cu', 'P03', '力学增强、电连续', 'The embedded Cu current collector'),
    (8, '问题', 'Li2S 充电难以完全分解', 'P11', '研究对象', '正极内部', '', '', '', 'a complete decomposition of Li2S during charge is difficult'),
    (8, '问题', 'Li2S 电子电导低', 'P05', '研究对象', '正极内部', '', '', '', 'the low electronic conductivity or the low ionic conductivity of Li2S'),
    (8, '问题', 'Li2S 离子电导低', 'P04', '研究对象', '正极内部', '', '', '', 'the low electronic conductivity or the low ionic conductivity of Li2S'),
    (8, '策略', '升温提高 Li⁺ 传导', 'S14', '研究变量（待定）', '电池整体', '', 'P11', '高温下 Li2S 分解变容易', 'introduces the factor of temperature to boost battery performance'),
    (9, '问题', '多硫化物穿梭', 'P10', '背景提及', '正极内部', '', '', '', 'the polysulfide shuttle'),
    (9, '问题', '锂枝晶', 'P01', '背景提及', '负极侧', '', '', '', 'lithium‐dendrite problems'),
    (9, '问题', '电极-电解质界面离子接触', 'P03', '研究对象', '未明确', '', '', '', 'the electrode–electrolyte interfaces'),
    (9, '问题', 'LATP 被锂金属还原', 'P02', '研究对象', '负极侧', '', '', '', 'susceptible to reaction with both the Li‐metal anode and polysulfides'),
    (9, '问题', 'LATP 被多硫化物还原', 'P02', '研究对象', '正极-电解质界面', '', '', '', 'susceptible to reaction with both the Li‐metal anode and polysulfides'),
    (9, '策略', 'PIN 聚合物薄层隔开锂与 LATP', 'S06', '本文实施', '负极侧', 'PIN（本征纳米孔聚合物）；LATP', 'P02', '避免 LATP 被锂还原', 'the PIN layer prevents the direct contact of Li‐metal with the LATP solid electrolyte'),
    (9, '策略', 'PIN 聚合物薄层阻挡多硫化物到达 LATP', 'S06', '本文实施', '正极-电解质界面', 'PIN；LATP', 'P02', '避免 LATP 被多硫化物还原', 'the PIN layer prevents the migration of polysulfides to the surface of LATP'),
    (10, '问题', '电解质层难减薄致电池级能量密度低', 'P14', '研究对象', '电池整体', '', '', '', 'low cell-level energy density due to the challenges in reducing the electrolyte thickness'),
    (10, '策略', '正极支撑的薄固态电解质层', 'S15', '本文实施', '电池整体', '不锈钢网；Li2S 正极', 'P14', '', 'cathode-supported ASSLBs with a thin solid electrolyte layer'),
    (10, '策略', 'Kevlar 无纺布增强 Li3PS4 电解质', 'S03', '本文实施', '电解质本体', 'Li3PS4；Kevlar 无纺布', 'P14', '', 'Li 3 PS 4 electrolyte reinforced by a Kevlar nonwoven scaffold'),
    (11, '问题', '多硫化物在聚合物电解质中穿梭', 'P10', '研究对象', '正极内部（待定）', '', '', '', 'of lithium polysulfide intermediates in the SPEs'),
    (11, '问题', '锂负极与聚合物电解质界面相容性差', 'P02', '研究对象', '负极侧', '', '', '', 'the low interfacial compatibility between the metal lithium anode and the SPE'),
    (11, '策略', 'ALD 沉积 Al2O3 于聚合物电解质表面', 'S06', '本文实施', '未明确', 'Al2O3；PEO-LiTFSI', 'P10；P02', '抑制枝晶、低自放电', 'atomic layer deposition of Al 2 O 3'),
    (12, '策略', '阳离子型多孔有机框架填料加入 PEO/LiTFSI', 'S03', '本文实施', '电解质本体', 'DB-POF；LB-POF；PEO/LiTFSI', '未明确', '提高离子电导、力学、锂负极稳定', 'were incorporated into a PEO/LiTFSI matrix as fillers'),
    (14, '问题', '多硫化物溶解', 'P10', '背景提及', '正极内部', '', '', '', 'polysulfide dissolution'),
    (14, '问题', '正极导电性差', 'P05', '背景提及', '正极内部', '', '', '', 'poor cathode conductivity'),
    (14, '问题', '体积变化大', 'P12', '背景提及', '正极内部', '', '', '', 'large volume change'),
    (14, '问题', '金属负极枝晶', 'P01', '背景提及', '负极侧', '', '', '', 'dendrite formation at metal anodes'),
    (14, '问题', '室温电导率不高', 'P04', '研究对象', '电解质本体', '', '', '', 'modest room-temperature conductivity'),
    (14, '问题', '界面电阻', 'P03', '研究对象', '未明确', '', '', '', 'interfacial resistance'),
    (14, '问题', '脆性', 'P08', '研究对象', '电解质本体', '', '', '', 'brittleness'),
    (14, '问题', '规模化加工', 'P16', '研究对象', '电池整体', '', '', '', 'scalable processing'),
    (14, '策略', '无机/聚合物/杂化固态电解质', 'S01', '背景提及', '电解质本体', '', 'P10；P05；P12；P01', '', 'solid-state electrolytes (SSEs) based on inorganic ceramics, polymers, and hybrid frameworks'),
    (14, '策略', '复合结构与界面工程（笼统）', 'S99', '背景提及', '未明确', '', '', '', 'design rules for composite architecture and interface engineering'),
    (15, '问题', '厚电极离子电子传输受阻', 'P13', '研究对象', '正极内部', '', '', '', 'severely hindered ion and electron transport in thick electrodes'),
    (15, '问题', '穿梭加剧', 'P10', '研究对象', '正极内部', '', '', '', 'exacerbated polysulfide shuttling and sluggish conversion kinetics'),
    (15, '问题', '转化动力学慢', 'P11', '研究对象', '正极内部', '', '', '', 'exacerbated polysulfide shuttling and sluggish conversion kinetics'),
    (15, '问题', '体积变化致机械退化', 'P12', '研究对象', '正极内部', '', '', '', 'mechanical degradation due to large volume changes'),
    (15, '策略', '结构设计构建传输通道', 'S08', '背景提及', '正极内部', '', 'P13', '', 'building efficient transport pathways through structural design'),
    (15, '策略', '催化转化', 'S09', '背景提及', '正极内部', '', 'P11', '', 'enhancing catalytic conversion'),
    (15, '策略', '界面与电解液工程（笼统）', 'S99', '背景提及', '未明确', '', 'P10', '', 'suppressing the shuttle effect via interface and electrolyte engineering'),
    (15, '策略', '稳固结构与功能粘结剂', 'S11', '背景提及', '正极内部', '', 'P12', '', 'robust architectures and functional binders'),
    (16, '问题', '多硫化物穿梭', 'P10', '背景提及', '正极内部', '', '', '', 'notorious shuttling of soluble polysulfide intermediates'),
    (16, '问题', '硫利用率低', 'P13', '背景提及', '正极内部', '', '', '', 'low S utilization'),
    (16, '问题', '锂负极腐蚀', 'P02', '背景提及', '负极侧', '', '', '', 'corrosion of the lithium anode'),
    (16, '策略', 'MWCNTs/LLTO 隔膜修饰', 'S07', '本文实施', '隔膜或中间层（待定）', '多壁碳纳米管；LLTO', 'P10；P13；P02', '促进多硫化物转化、物理阻挡', 'a modified separator composed of multi-walled carbon nanotubes/lithium lanthanum titanium oxide (MWCNTs/LLTO)'),
    (17, '问题', 'SEI 难控制、锂负极循环稳定性差', 'P02', '研究对象', '负极侧', '', '', '', 'Controlling the composition and microstructure of the solid electrolyte interphase (SEI) layer is critical'),
    (17, '策略', '旋涂 Li3PS4 人工 SEI 层', 'S06', '本文实施', '负极侧', 'Li3PS4', 'P02', '均匀 Li⁺ 通量、阻止副反应、缓解浓差极化', 'Li 3 PS 4 artificial SEI layer with a controllable nanoscale thickness'),
    (18, '问题', '固态硫氧化还原机理不清', 'P17', '研究对象', '正极内部', '', '', '', 'The sulfur redox mechanism in solid-state lithium–sulfur (Li–S) batteries remains unclear'),
    (18, '问题', '反应动力学慢', 'P11', '背景提及', '正极内部', '', '', '', 'sluggish reaction kinetics'),
    (18, '策略', '用高离子电导固态电解质减轻动力学限制', 'S01', '本文实施', '电解质本体', 'Li5.5PS4.5Cl1.5', 'P11', '', 'using solid electrolytes with high ionic conductivities to mitigate kinetic limitations'),
    (19, '策略', '聚(β-氨基酯)梳状聚合物与 PEO 互穿', 'S04', '本文实施', '电解质本体', '聚(β-氨基酯)；PEO', '未明确', '离子传输通道；促进电极表面多硫化物转化', 'an expanded interpenetrating macromolecular engineering approach'),
    (20, '问题', '多硫化物穿梭', 'P10', '研究对象', '正极内部', '', '', '', 'polysulfide shuttle effect'),
    (20, '问题', '锂枝晶', 'P01', '研究对象', '负极侧', '', '', '', 'lithium dendrite growth'),
    (20, '问题', '容量衰减、寿命短、倍率差', '不计', '背景提及', '电池整体', '', '', '', 'rapid capacity fading, short cycle life, and low-rate capability'),
    (20, '策略', 'PEO + 可降解纤维素填料', 'S03', '背景提及', '电解质本体', 'PEO；纤维素', 'P01；P10', '', 'polyethylene oxide (PEO) electrolytes reinforced with biodegradable cellulose fillers'),
    (20, '策略', '正极催化材料', 'S09', '背景提及', '正极内部', '', 'P10', '', 'cathode designs that incorporate catalytic materials, Lewis acid-base sites and polar adsorbents'),
    (20, '策略', '正极路易斯酸碱位点、极性吸附剂', 'S10', '背景提及', '正极内部', '', 'P10', '', 'cathode designs that incorporate catalytic materials, Lewis acid-base sites and polar adsorbents'),
    (20, '策略', '选择性阻挡多硫化物的隔膜', 'S07', '背景提及', '隔膜或中间层（待定）', '', 'P10', '', 'advanced separators to selectively block polysulfides'),
    (21, '策略', '室温化学预锂化制 Li2S 正极', 'S13', '本文实施', '正极内部', '萘锂', '未明确', '比高温预锂化容量高、迟滞小', 'dropping the organolithium reagent lithium naphthalenide'),
    (21, '策略', '3D CNT 集流体', 'S08', '本文实施', '正极内部', '碳纳米管', '未明确', '使室温预锂化可行', '3D nanostructured carbon nanotube (CNT) current collector'),
    (22, '问题', '硫利用率随硫浓度升高而下降', 'P13', '研究对象', '正极内部', '', '', '', 'The sulfur utilization decreased gradually from 74 to 40%'),
    (22, '问题', '高硫浓度下欧姆降和过电位大', 'P99', '研究对象', '未明确', '', '', '', 'significant ohmic drop and large reaction overpotential'),
    (22, '策略', '改变硫浓度（参数研究）', 'S99', '研究变量（待定）', '未明确', '', 'P13', '', 'the influence of the sulfur concentration on the electrochemical properties'),
    (23, '问题', '正极表面循环中变粗糙', 'P12', '研究对象', '正极内部', '', '', '', 'the sulfur-carbon cathode becomes rougher'),
    (24, '问题', '正极硫流失', 'P10', '背景提及', '正极内部', '', '', '', 'The loss of sulfur in the cathode'),
    (24, '问题', '硫和放电产物绝缘', 'P05', '背景提及', '正极内部', '', '', '', 'the insulativity of S and its lithiation end products'),
    (24, '策略', 'MXene 添加剂（计算）', 'S10', '本文实施（计算）', '正极内部', 'Ti 基 MXene（含 -F、-O、-OH 端基）', 'P10；P05', '强 Ti–S 键锚定、导电', 'The incorporation of MXene can significantly improve the performance of LSBs'),
    (25, '问题', '多硫化物溶解', 'P10', '研究对象', '正极内部', '', '', '', 'the dissolution of lithium polysulfides'),
    (25, '策略', '离子液体作电解液溶剂', 'S01', '本文实施', '电解质本体', '[DEME][TFSA]', 'P10', '低供体能力抑制多硫化物溶解', 'was used as an electrolyte solvent for lithium–sulfur (Li–S) batteries'),
    (26, '问题', '硫和放电产物导电性低', 'P05', '背景提及', '正极内部', '', '', '', 'the low conductivity of sulfur and its discharge products'),
    (26, '问题', '硫电极体积膨胀', 'P12', '背景提及', '正极内部', '', '', '', 'volume expansion of sulfur electrode'),
    (26, '问题', '多硫化物穿梭', 'P10', '背景提及', '正极内部', '', '', '', 'the polysulfide shuttle effect'),
    (26, '策略', '金属基化合物作硫宿主', 'S10', '背景提及', '正极内部', '金属磷化物、硫化物、氧化物、MXene 等', 'P10', '极性吸附', 'metal‐based compounds'),
    (26, '策略', '复合导电碳', 'S08', '背景提及', '正极内部', '导电碳', 'P05', '', 'the integration of conductive carbon‐based materials'),
    (26, '策略', '催化剂设计', 'S09', '背景提及', '正极内部', '', '', '', 'smart design of catalysts'),
    (28, '问题', '已有宿主活性位点暴露少', 'P99', '研究对象', '正极内部', '', '', '', 'their exposures as active sites to adsorb polysulfides are limited'),
    (28, '策略', 'TiO2 纳米颗粒锚定于含 Co 碳多面体', 'S10', '本文实施', '正极内部', 'TiO2；Co；ZIF-67 衍生碳', 'P99', '更多活性位点、强化学吸附、提高利用率和动力学', 'highly dispersed TiO2 nanoparticles are anchored into the cobalt‐containing carbon polyhedras'),
    (29, '问题', '多硫化物穿梭', 'P10', '背景提及', '正极内部', '', '', '', 'lithium polysulfides (LiPSs) shuttling effect on the S cathode'),
    (29, '问题', '锂枝晶', 'P01', '背景提及', '负极侧', '', '', '', 'uncontrollable Li‐dendrite growth on the Li anode'),
    (29, '策略', 'WSe2/N 掺杂石墨烯作正极氧化还原促进剂', 'S09', '本文实施', '正极内部', 'WSe2；N 掺杂石墨烯', 'P10', '促进多硫化物双向转化', 'can act as a redox accelerator to promote the bidirectional conversion of LiPSs'),
    (29, '策略', 'WSe2/N 掺杂石墨烯作负极亲锂宿主', 'S12', '本文实施', '负极侧', 'WSe2；N 掺杂石墨烯', 'P01', '均匀沉积锂', 'can regulate the uniform Li plating/stripping to mitigate the growth of Li dendrite'),
    (30, '问题', '电解液过量，达不到贫液', 'P14', '研究对象', '电池整体', '', '', '', 'mainly because of the electrolyte excess'),
    (30, '策略', '聚电解质复合纳米颗粒涂层隔膜', 'S07', '本文实施', '隔膜或中间层（待定）', '聚电解质复合纳米颗粒；Celgard', 'P14', '贫液下调控多硫化物、保持传输', 'polyelectrolyte complex nanoparticle decorated (PPX) separator'),
    (31, '问题', '多硫化物扩散', 'P10', '背景提及', '正极内部', '', '', '', 'intercepting the diffusing polysulfides'),
    (31, '问题', '隔膜 Li⁺ 传输调控研究少', 'P17', '研究对象', '隔膜或中间层（待定）', '', '', '', 'offering limited investigation on the tuning of Li+ transfer across the separators'),
    (31, '策略', 'MOF 三层阶梯通道隔膜', 'S07', '本文实施', '隔膜或中间层（待定）', 'MOF', 'P10；P17', '', 'a triple‐layer separator with stepped‐channels'),
    (32, '问题', '活性物体积变化', 'P12', '背景提及', '正极内部', '', '', '', 'the considerable volume change of the active material'),
    (32, '策略', '等离子体制 N 掺杂 3D 石墨烯框架', 'S08', '本文实施', '正极内部', 'N 掺杂石墨烯', 'P12', '导电基体、电催化、容纳体积变化', '3D porous frameworks based on N‐doped graphene'),
    (33, '问题', 'S 与 Li2S 转化动力学慢', 'P11', '研究对象', '正极内部', '', '', '', 'slow conversion kinetics between the insulating S and lithium sulfide'),
    (33, '策略', 'Ni 单原子/团簇锚定于氢取代石墨炔催化剂', 'S09', '本文实施', '正极内部', 'Ni@HGDY', 'P11', '提高离子电子电导、降低过电位', 'nickel (Ni) single atoms and clusters anchored to a porous hydrogen-substituted graphdiyne support'),
    (34, '策略', 'SPAN 正极 + 软包整体设计', 'S15', '本文实施', '电池整体', 'SPAN', '未明确', '电池级比能量 >700 Wh/kg', 'designed by combining the SPAN cathode and state-of-the-art technologies'),
    (35, '问题', '多硫化物穿梭', 'P10', '背景提及', '正极内部', '', '', '', 'suppresses the shuttle effect'),
    (35, '策略', '二维联苯烯作锚定材料（计算）', 'S10', '本文实施（计算）', '正极内部', '联苯烯', 'P10', '', 'biphenylene, as an anchoring material for the lithium-sulfur battery'),
    (35, '策略', '单 C 空位缺陷工程（计算）', 'S02', '本文实施（计算）', '正极内部', '联苯烯', 'P10', '提高结合强度', 'defect engineering through a single C atom vacancy'),
    (36, '策略', '生物质衍生多孔碳及其修饰', 'S08', '背景提及', '正极内部', '生物质碳', '', '', 'biomass derived porous carbons'),
    (37, '问题', '多硫化物穿梭', 'P10', '背景提及', '正极内部', '', '', '', 'suppressing the shuttle effect of polysulfides'),
    (37, '策略', '大豆蛋白-聚多巴胺功能粘结剂', 'S11', '本文实施', '正极内部', '大豆蛋白；聚多巴胺', 'P10', '捕获多硫化物', 'networking soy protein (SP) and polydopamine (PDA)'),
    (37, '策略', '正极表面石墨烯涂层', 'S05', '本文实施', '正极-电解质界面', '石墨烯', 'P10', '降低阻抗、减少多硫化物溶解', 'the Gr coating with low impedance'),
    (38, '问题', '穿梭效应严重', 'P10', '背景提及', '正极内部', '', '', '', 'severe shuttle effects'),
    (38, '问题', '动力学慢', 'P11', '背景提及', '正极内部', '', '', '', 'sluggish kinetics'),
    (38, '策略', 'O/F 端基 MXene 锚定材料（计算）', 'S10', '本文实施（计算）', '正极内部', 'Mo2CF2；V2CF2', 'P10；P11', '', 'O/F-covered MXene'),
    (39, '问题', '穿梭导致多硫化物损失', 'P10', '背景提及', '正极内部', '', '', '', 'the loss of lithium polysulfides (LiPSs) caused by the shuttling effect'),
    (39, '问题', '双向转化电催化剂缺少设计原则', 'P17', '研究对象', '正极内部', '', '', '', 'the design rationale of electrocatalysts to drive roundtrip sulfur/sulfide conversion is lacking'),
    (39, '策略', '路易斯酸碱位点配对的电催化剂', 'S09', '本文实施', '正极内部', '偏钨酸根掺杂聚苯胺', 'P11', '降低双向反应活化能', 'doping polyaniline with protonated metatungstate anions'),
    (42, '策略', '气相 SiO2 填料', 'S03', '本文实施', '电解质本体', '气相 SiO2；壳聚糖', '未明确', '电导率提高', 'different concentrations of fumed silica (SiO2) as the inorganic filler'),
    (42, '策略', 'EC/PC 增塑剂', 'S03', '本文实施', '电解质本体', 'EC；PC', '未明确', '', 'ethylene carbonate and propylene carbonate as the plasticisers'),
    (43, '问题', '室温制备薄膜残留 Li2CO3 难分解', 'P09', '研究对象', '正极内部', '', '', '', 'was hard to decompose fully'),
    (43, '策略', '调节沉积基底温度', 'S13', '本文实施', '正极内部', 'LiCoO2 薄膜', 'P09', '多晶结构利于锂嵌入', 'the substrate temperature of 150℃'),
    (44, '问题', '与空气或水中的水反应', 'P07', '研究对象', '电解质本体', '', '', '', 'the reactivity with water either from the air or in aqueous media'),
    (45, '问题', '固态聚合物电解质离子传输', 'P04', '研究对象', '电解质本体', '', '', '', 'improve the ion transport properties of solid polymer electrolytes'),
    (45, '策略', '加入离子液体', 'S03', '背景提及', '电解质本体', '离子液体', 'P04', '', 'the use of ionic liquids (ILs)'),
    (45, '策略', '嵌段共聚物自组装形貌', 'S04', '背景提及', '电解质本体', '嵌段共聚物', 'P04', '', 'by the use of block copolymers'),
    (46, '策略', 'Sc(OTf)3 催化 DOL 开环聚合原位制准固态电解质', 'S01', '本文实施', '电解质本体', 'Sc(OTf)3；1,3-二氧戊环', '未明确', '电导率高、无枝晶', 'a rare-earth triflate catalyst Sc(OTf)3 for the ring-opening polymerization of 1,3-dioxolane'),
    (47, '策略', 'UV 交联 LLZO/PEO/四甘醇二甲醚复合聚合物电解质', 'S04', '本文实施', '电解质本体', 'LLZO；PEO；四甘醇二甲醚', '未明确', '室温高电导、不燃、保形', 'cross-linked composite polymer electrolyte (CPE) based on the garnet-type ceramic'),
    (48, '问题', '固态电解质离子电导需提高', 'P04', '研究对象', '电解质本体', '', '', '', 'Developing solid electrolytes with high lithium-ion conductivity is crucial'),
    (48, '策略', 'Ti⁴⁺ 部分取代 Ge⁴⁺', 'S02', '本文实施', '电解质本体', 'TiO2；LAGP', 'P04', '扩大迁移通道、减少晶界', 'is employed to partially replace Ge'),
    (49, '问题', '枝晶', 'P01', '研究对象', '负极侧', '', '', '', 'suppressing dendrite growth'),
    (49, '问题', '湿度稳定性', 'P07', '研究对象', '电解质本体', '', '', '', 'improving moisture stability'),
    (49, '问题', '界面电阻高', 'P03', '研究对象', '负极侧', '', '', '', 'reducing interfacial resistance'),
    (49, '问题', '表面杂质 Li2CO3、LiOH', 'P07', '研究对象', '电解质本体', '', '', '', 'primary surface contaminants such as lithium carbonate'),
    (49, '策略', '氩离子溅射或高温退火去除表面杂质', 'S13', '本文实施', '电解质本体', 'LLZT', 'P07', '', 'argon-ion sputtering at 227 °C or annealing at 777 °C'),
    (49, '策略', '原位 ALD 沉积约 3 nm h-BN 保护层', 'S06', '本文实施', '负极侧', 'h-BN；LLZT', 'P07；P03', '界面电阻降约 65 倍', 'atomic layer deposition was used to deposit'),
    (50, '问题', '硫化物电解质与氧化物正极反应', 'P02', '研究对象', '正极-电解质界面', '', '', '', 'sulfides are very reactive with oxide cathodes'),
    (50, '策略', 'Li2ZrO3 包覆 NCA', 'S05', '本文实施', '正极-电解质界面', 'Li2ZrO3；NCA', 'P02', '抑制 S、P 向正极扩散', 'a Li2ZrO3 coated Li[Ni0.8Co0.15Al0.05]O2 (NCA) cathode'),
    (51, '问题', '填料分散', 'P16', '研究对象', '电解质本体', '', '', '', 'strategies for dispersing fillers'),
    (51, '策略', '填料工程（复合聚合物电解质）', 'S03', '背景提及', '电解质本体', '', 'P16', '', 'combine polymer electrolytes with various fillers'),
    (52, '问题', '锂枝晶', 'P01', '背景提及', '负极侧', '', '', '', 'mitigating dendritic lithium (Li) growth'),
    (52, '问题', '凝胶电解质离子电导、迁移数、理化性能不足', 'P04', '研究对象', '电解质本体', '', '', '', 'inadequate ionic conductivity, low Li+ transference number, and subpar physicochemical properties'),
    (52, '策略', '含氧空位 TiO2−x 纳米纤维填料', 'S03', '本文实施', '电解质本体', 'TiO2−x 纳米纤维', 'P04', '促进 LiPF6 解离、富 LiF SEI', 'nanofibers (NF) with oxygen vacancy defects'),
    (53, '问题', '70 °C 发生相变', 'P09', '研究对象', '电解质本体', '', '', '', 'phase transformation was observed'),
    (53, '策略', '优化球磨时间、温度、压力', 'S13', '本文实施', '电解质本体', 'Li3InCl6', 'P04', '室温电导 0.98 mS/cm', 'ball-milling time, temperature, and pressure'),
    (54, '问题', '枝晶', 'P01', '研究对象', '负极侧', '', '', '', 'dendrite formation'),
    (54, '问题', '副反应', 'P02', '研究对象', '负极侧', '', '', '', 'side reactions'),
    (54, '问题', '空洞裂纹', 'P03', '研究对象', '负极侧', '', '', '', 'voids and cracks formed during battery fabrication/operation are hot spots for failure'),
    (54, '策略', '自修复可流动固态电解质', 'S01', '本文实施', '电解质本体', '可移动陶瓷晶体；可重构聚合物网络', 'P03；P01', '修复空洞裂纹、近零堆压下循环', 'mobile ceramic crystals embedded in a reconfigurable polymer network'),
    (55, '问题', '锂化合金硬脆需高堆压', 'P08', '研究对象', '负极侧', '', '', '', 'requiring commercially impractical stack pressures during operation'),
    (55, '策略', 'In、Sn 原子级混合引入纳米非晶结构', 'S12', '本文实施', '负极侧', 'In；Sn', 'P08', '堆压需求从 ≥30 降到 ≤5 MPa', 'atomically mixed In and Sn generate abundant nanoscale amorphous structures during lithiation'),
    (56, '问题', '非导电杂相', 'P09', '研究对象', '电解质本体', '', '', '', 'nonconducting impurity phases'),
    (56, '策略', 'Ta 取代 LLZO', 'S02', '本文实施', '电解质本体', 'Ta', '未明确', '', 'Ta-substituted lithium-conducting solid electrolyte powders'),
    (56, '策略', '低熔点结晶水合物熔融后固相烧结', 'S13', '本文实施', '电解质本体', '', 'P09', '单相立方', 'by melting a charge consisting of low-melting crystallohydrates'),
    (57, '问题', '与金属负极界面不稳定', 'P02', '研究对象', '负极侧', '', '', '', 'interfacial instability with metal anodes'),
    (57, '问题', '枝晶形成与穿透', 'P01', '研究对象', '负极侧', '', '', '', 'leading to dendrite formation and penetration'),
    (57, '策略', '电解质、电极、界面缓解策略（笼统）', 'S99', '背景提及', '未明确', '', 'P02；P01', '', 'mitigation strategies targeting the electrolyte, electrode, and their interface'),
    (58, '问题', '电化学窗口预测与实验偏差大', 'P17', '研究对象', '电解质本体', '', '', '', 'the large deviation between the predicted ESW and the experimental one'),
    (58, '策略', '动态确定分解路径的窗口预测方法', 'S17', '本文实施（计算）', '电解质本体', '', 'P17', '', 'ESW prediction method is proposed'),
    (58, '策略', '筛选出六种氟化物电解质', 'S01', '本文实施（计算）', '电解质本体', '氟化物', 'P06', '窗口 >4 V', 'six previously neglected fluorides'),
    (60, '问题', '界面离子传输不连续', 'P03', '研究对象', '未明确', '', '', '', 'discontinuous interfacial ion/charge transport'),
    (60, '问题', '电解质在高压下持续降解', 'P06', '研究对象', '正极-电解质界面', '', '', '', 'continuous degradation of the electrolyte'),
    (60, '策略', '阴离子调控聚碳酸亚乙烯酯链构象原位构建界面相', 'S04', '本文实施', '电解质本体', '聚碳酸亚乙烯酯；锂盐阴离子', 'P03；P06', '4.5 V 下 200 圈保持 85%', 'exploiting conformational transitions under multiple interactions between polymer and lithium salt anions'),
]

QUESTIONS = [
    ('Q1 位置', '液态锂硫的隔膜修饰、正极侧中间层放在哪个位置？本批临时记"隔膜或中间层（待定）"。另外"多硫化物穿梭"统一记在正极内部（问题的源头），聚合物电解质里的穿梭（#11）也这样记，行不行？'),
    ('Q2 性能症状', '"容量衰减、寿命短、倍率差"这类结果描述不作问题标签（本批记"不计"），只记作者给出的具体原因。同意吗？'),
    ('Q3 知识型问题', '"机理不清""缺少设计原则""预测不准"不是电池里的物理问题。本批暂记 P17。是保留为单独一类，还是不记？'),
    ('Q4 纯电解质研究', '只做锂对称电池、没有含正极电池测试的论文（#2、#46），算不算"纯电解质研究"？建议：没有含正极的电池测试 = 纯电解质研究；对称电池另记在"实验配置"里。'),
    ('Q5 策略角色', '参数研究（#8 温度、#22 硫浓度）不是"实施的策略"。本批新增角色"研究变量（待定）"。是否保留？'),
    ('Q6 计算论文', 'DFT 筛选的锚定材料（#24、#35、#38）本批角色记"本文实施（计算）"，统计时要不要和实验论文分开？'),
    ('Q7 含液聚合物', '含增塑剂、离子液体、四甘醇二甲醚的聚合物电解质（#42、#45、#47），液相状态记"含液或凝胶"还是"全固态"？这决定它们进不进非硫固态。'),
    ('Q8 复合正极', '新增策略 S16"复合正极配比与微结构"（本批只出现 1 次，在综述里）。这是第二层试点主题的核心，建议保留，即使摘要层很少出现。'),
]


def norm(s):
    s = unicodedata.normalize('NFKC', s)
    s = re.sub(r'[‐-―−]', '-', s)
    s = s.replace('“', '"').replace('”', '"').replace('’', "'")
    return re.sub(r'\s+', ' ', s).strip().lower()


def main(sample_csv, paper_csv, out):
    s = pd.read_csv(sample_csv, dtype=str)
    s = s[s['批次'] == '1'].reset_index(drop=True)
    s['序号'] = range(1, len(s) + 1)
    p = pd.read_csv(paper_csv, dtype=str).fillna('').set_index('编号')
    s['标题'] = s['论文号'].map(p['标题'])
    s['摘要'] = s['论文号'].map(p['摘要'])
    meta = s.set_index('序号')

    pap = pd.DataFrame(PAPERS, columns=['序号', '组别核查', '建议归属', '理由', '文献类型', '液相状态', '负极类型', '实验配置', '纯电解质研究'])
    pap = meta[['论文号', 'DOI', '年份', '组', '材料类别']].rename(columns={'组': '旧分组', '材料类别': '旧材料标签'}).join(pap.set_index('序号')).reset_index()
    pap.insert(5, '标题', pap['序号'].map(meta['标题']))

    it = pd.DataFrame(ITEMS, columns=['序号', '类型', '开放描述', '词表标签', '角色', '位置', '具体物质', '针对的问题', '声称作用', '原文短语'])
    it.insert(0, '标注号', [f'B1-{i:03d}' for i in range(1, len(it) + 1)])
    it.insert(2, '论文号', it['序号'].map(meta['论文号']))
    it.insert(3, '旧分组', it['序号'].map(meta['组']))

    def check(r):
        text = meta.loc[r['序号'], '标题'] + ' ' + meta.loc[r['序号'], '摘要']
        if r['原文短语'] in text:
            return '程序核验通过', '✅'
        if norm(r['原文短语']) in norm(text):
            return '程序核验通过（字符规范化后）', '✅'
        return '原文未找到', '❌'
    it[['核验状态', '显示']] = it.apply(lambda r: pd.Series(check(r)), axis=1)
    it['复核 ✍'] = ''

    plab = dict((a, b) for a, b, _ in PROBLEMS)
    slab = dict((a, b) for a, b, _ in STRATEGIES)
    it.insert(7, '标签名', [plab.get(t, '') if k == '问题' else slab.get(t, '') for k, t in zip(it['类型'], it['词表标签'])])

    # 词表页：每个标签在三组里的出现（原始条数 / 去重后论文数）
    def vocab_sheet(defs, kind):
        rows = []
        sub = it[it['类型'] == kind]
        for code, name, desc in defs:
            x = sub[sub['词表标签'] == code]
            row = {'标签': code, '名称': name, '定义': desc, '原始条数': len(x)}
            for g in ['固态锂硫', '液态锂硫', '非硫固态']:
                row[f'{g}·论文数'] = x[x['旧分组'] == g]['论文号'].nunique()
            row['例句'] = ' | '.join(x['原文短语'].head(3))
            rows.append(row)
        return pd.DataFrame(rows)
    pv, sv = vocab_sheet(PROBLEMS, '问题'), vocab_sheet(STRATEGIES, '策略')

    # 汇总：按 论文号 + 标签 + 角色 去重
    d = it.drop_duplicates(['论文号', '词表标签', '角色'])
    summ = d.pivot_table(index=['类型', '词表标签', '角色'], columns='旧分组', values='论文号', aggfunc='nunique', fill_value=0).reset_index()

    q = pd.DataFrame(QUESTIONS, columns=['编号', '要你定的问题'])
    q['你的决定 ✍'] = ''

    note = pd.DataFrame({'说明': [
        '方案D §9.1 词表试点·批1（60 篇摘要，2026-10-18）。',
        '论文核查：每篇的组别、液相状态、负极、实验配置、是否纯电解质研究。"建议归属"只是 Claude 根据摘要的判断，不改冻结的论文表。',
        '开放抽取：一行 = 一篇里的一处问题或策略，原始标注不去重；"原文短语"由代码到标题+摘要里逐字核对（✅ 找到 / ❌ 没找到）。',
        '词表 v0：从开放描述归纳。问题按"现象"分类，位置另记一列；策略按"做法"分类，位置另记。',
        '汇总：按 论文号 + 标签 + 角色 去重后的论文数，按旧分组列出（旧分组本身有误，见论文核查页）。',
        '待你定：Q1–Q8，决定后修订词表，再用批2 检验。',
    ]})

    with pd.ExcelWriter(out, engine='openpyxl') as w:
        note.to_excel(w, '说明', index=False)
        pap.to_excel(w, '论文核查', index=False)
        it.to_excel(w, '开放抽取', index=False)
        pv.to_excel(w, '问题词表v0', index=False)
        sv.to_excel(w, '策略词表v0', index=False)
        summ.to_excel(w, '汇总', index=False)
        q.to_excel(w, '待你定', index=False)
        for ws in w.book.worksheets:
            ws.freeze_panes = 'A2'
            for col in ws.columns:
                width = max(len(str(c.value)) if c.value is not None else 0 for c in col[:60])
                c0 = col[0].column
                letter = c0 if isinstance(c0, str) else get_column_letter(c0)  # 旧版 openpyxl 直接给字母
                ws.column_dimensions[letter].width = min(max(8, width * 1.1), 60)

    print('条目数：', len(it), '｜问题', (it['类型'] == '问题').sum(), '｜策略', (it['类型'] == '策略').sum())
    print('核验：', it['核验状态'].value_counts().to_dict())
    bad = it[it['显示'] == '❌']
    if len(bad):
        print('未找到：'); print(bad[['标注号', '序号', '原文短语']].to_string())
    print('\n组别核查（按旧分组）：'); print(pd.crosstab(pap['旧分组'], pap['组别核查']).to_string())
    print('\n"其他/不确定"占比：问题', round((it[it['类型'] == '问题']['词表标签'] == 'P99').mean() * 100, 1), '%｜策略',
          round((it[it['类型'] == '策略']['词表标签'] == 'S99').mean() * 100, 1), '%')


if __name__ == '__main__':
    main(*sys.argv[1:4])
