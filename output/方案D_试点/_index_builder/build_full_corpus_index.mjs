import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "D:/Desktop/课题一锂硫知识流动分析/output/方案D_试点";
const data = JSON.parse(await fs.readFile(`${root}/全库文献索引_中间数据.json`, "utf8"));
const outPath = `${root}/全库文献索引.xlsx`;
const selectedReasons = new Map();
function selectTransfer(group, bridgeN, recentN) {
  const records = data.transfer_records.filter((r) => r["体系"] === group);
  const labels = new Set(records.flatMap((r) => (r["策略主题"] || "").split("；").filter(Boolean)));
  for (const label of labels) {
    const cohort = records.filter((r) => (r["策略主题"] || "").split("；").includes(label));
    const byBridge = [...cohort].sort((a, b) => Number(b["被固态锂硫库引用的篇数"] || 0) - Number(a["被固态锂硫库引用的篇数"] || 0) || Number(b["年份"] || 0) - Number(a["年份"] || 0));
    for (const r of byBridge.slice(0, bridgeN)) {
      const key = `${group}|${r["编号"]}`;
      if (!selectedReasons.has(key)) selectedReasons.set(key, new Set());
      selectedReasons.get(key).add(`${label}：被固态锂硫引用较多`);
    }
    const recent = cohort.filter((r) => Number(r["年份"] || 0) >= 2022)
      .sort((a, b) => Number(b["年份"] || 0) - Number(a["年份"] || 0) || Number(b["被固态锂硫库引用的篇数"] || 0) - Number(a["被固态锂硫库引用的篇数"] || 0));
    for (const r of recent.slice(0, recentN)) {
      const key = `${group}|${r["编号"]}`;
      if (!selectedReasons.has(key)) selectedReasons.set(key, new Set());
      selectedReasons.get(key).add(`${label}：2022年后文献`);
    }
  }
}
selectTransfer("液态锂硫", 35, 25);
selectTransfer("固态锂金属/负极相关固态电池", 35, 25);
for (const r of data.transfer_records.filter((x) => x["体系"] === "准固态锂硫（边界对照）")) {
  selectedReasons.set(`${r["体系"]}|${r["编号"]}`, new Set(["准固态边界对照候选全纳入"]));
}
const selectedTransferRecords = data.transfer_records.filter((r) => selectedReasons.has(`${r["体系"]}|${r["编号"]}`));
const wb = Workbook.create();
const overview = wb.worksheets.add("候选判断");
const strategies = wb.worksheets.add("方案对照");
const index = wb.worksheets.add("文献索引");
for (const sheet of [overview, strategies, index]) sheet.showGridLines = false;

const font = "Arial";
const navy = "#1F4E78";
const paleBlue = "#D9EAF7";
const gray = "#F2F2F2";
const bodyFont = { name: font, size: 10, color: "#202124" };
const headerFont = { name: font, size: 10, bold: true, color: "#FFFFFF" };

function styleTitle(sheet, cell, text) {
  sheet.getRange(cell).values = [[text]];
  sheet.getRange(cell).format.font = { name: font, size: 15, bold: true, color: "#1F1F1F" };
  sheet.getRange(cell).format.verticalAlignment = "center";
}
function styleHeader(sheet, range) {
  sheet.getRange(range).format = {
    fill: navy,
    font: headerFont,
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
  };
}
function addTable(sheet, range, name) {
  const table = sheet.tables.add(range, true, name);
  table.showFilterButton = true;
  table.style = "TableStyleMedium2";
  return table;
}
function countTag(tag, subset = data.solid_lis_records) {
  return subset.filter((r) => (r["主题标签"] || "").includes(tag)).length;
}
function countIntersection(tagA, tagB, subset = data.solid_lis_records) {
  return subset.filter((r) => (r["主题标签"] || "").includes(tagA) && (r["主题标签"] || "").includes(tagB)).length;
}
function numericYear(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}
function safeText(v) {
  const s = String(v ?? "");
  return s.startsWith("=") ? `'${s}` : s;
}

// Main decision view.
styleTitle(overview, "A1", "固态锂硫全库比较与主问题");
overview.getRange("A2:D2").values = [["进度", "", "", "主线已定；具体配方待全文条件对照。"]];
overview.getRange("A2:D2").format = { font: { name: font, size: 10, italic: true, color: "#666666" }, wrapText: false, verticalAlignment: "center" };
overview.getRange("A2:D2").format.rowHeight = 22;

overview.getRange("A4:D8").values = [
  ["文献池", "记录数", "有摘要", "筛选口径"],
  ["固态锂硫（主库）", data.summary.target["记录数"], data.summary.target["摘要数"], "1181条全量索引；题名+摘要多标签"],
  ["液态锂硫（来源池）", data.summary.source_pools["液态锂硫"]["记录数"], data.summary.source_pools["液态锂硫"]["摘要数"], `策略候选${data.summary.source_pools["液态锂硫策略主题命中"]}条；索引含桥接/近年样本`],
  ["固态锂电池（来源池）", data.summary.source_pools["固态锂电池"]["记录数"], data.summary.source_pools["固态锂电池"]["摘要数"], `锂金属/负极词命中${data.summary.source_pools["锂金属/负极词命中且有摘要"]}条；不把全组称作锂金属`],
  ["准固态锂硫（边界对照）", data.summary.source_pools["准固态锂硫"]["记录数"], data.summary.source_pools["准固态锂硫"]["摘要数"], "独立保留，不并入全固态目标组"],
];
styleHeader(overview, "A4:D4");
addTable(overview, "A4:D8", "CorpusScope");
overview.getRange("B5:C8").format.numberFormat = "#,##0";

const tags = Object.keys(data.summary.target_label_counts);
const targetRows = data.solid_lis_records;
const recentRows = targetRows.filter((r) => (numericYear(r["年份"]) || 0) >= 2023);
const topicTable = [["主题线索（可重叠）", "命中篇数", "2023–2026"]];
for (const tag of tags) topicTable.push([tag, countTag(tag), countTag(tag, recentRows)]);
overview.getRangeByIndexes(9, 0, topicTable.length, 3).values = topicTable;
styleHeader(overview, "A10:C10");
addTable(overview, `A10:C${9 + topicTable.length}`, "TopicCoverage");
overview.getRange(`B11:C${9 + topicTable.length}`).format.numberFormat = "#,##0";

const intersections = [
  ["主题交集（候选重叠）", "命中篇数"],
  ["载量/压力 × 界面/接触", countIntersection("载量压力与实用条件", "界面与接触")],
  ["载量/压力 × 碳网络", countIntersection("载量压力与实用条件", "碳宿主与电子网络")],
  ["载量/压力 × 电解质", countIntersection("载量压力与实用条件", "电解质组成与反应")],
  ["硫转化/正极 × 界面/接触", countIntersection("正极材料与硫转化", "界面与接触")],
  ["硫转化/正极 × 碳网络", countIntersection("正极材料与硫转化", "碳宿主与电子网络")],
  ["催化/介体 × 界面/接触", countIntersection("催化与介体", "界面与接触")],
];
overview.getRange("A19:B25").values = intersections;
styleHeader(overview, "A19:B19");
addTable(overview, "A19:B25", "TopicIntersections");
overview.getRange("B20:B25").format.numberFormat = "#,##0";
overview.getRange("A20:B25").format = { font: bodyFont, wrapText: true, verticalAlignment: "center" };
overview.getRange("A20:B25").format.rowHeight = 24;

overview.getRange("A27:D27").values = [["优先", "候选问题方向", "证据规模", "结论与全文核查重点"]];
styleHeader(overview, "A27:D27");
overview.getRange("A28:D31").values = [
  [1, "正极复合组成×比例×界面/结构", `正极${countTag("正极材料与硫转化")}；界面${countTag("界面与接触")}；碳网络${countTag("碳宿主与电子网络")}；正极∩界面${countIntersection("正极材料与硫转化", "界面与接触")}`, "定为课题一主问题。比较材料、比例、位置和加工如何共同控制硫利用、通路、接触及副反应。"],
  [2, "电解质参与硫转化", `电解质词项${countTag("电解质组成与反应")}；催化/介体${countTag("催化与介体")}；F专项78篇计入、53篇原创`, "作为主问题内的机制分支；分别判定可逆介体、分解生成活性相、不可逆消耗。"],
  [3, "高载硫/高面容量与运行条件", `载量/压力${countTag("载量压力与实用条件")}；2023–2026年${countTag("载量压力与实用条件", recentRows)}；载量/压力∩界面${countIntersection("载量压力与实用条件", "界面与接触")}`, "作为实用验证工况；统一硫载量、面容量、温度、倍率、截止电位与运行堆压后再比。"],
  [4, "单独替换一个介体/催化剂", `${countTag("催化与介体")}篇宽口径线索`, "暂不单独立题；要有明确选择规则或新组合证据，不能只换材料名称。"],
];
addTable(overview, "A27:D31", "CandidateAssessment");
overview.getRange("A28:A31").format.horizontalAlignment = "center";
overview.getRange("A28:D31").format = { font: bodyFont, wrapText: true, verticalAlignment: "top" };
overview.getRange("A28:D31").format.rowHeight = 58;

overview.getRange("A33:D33").values = [["主问题", "", "", "固态锂硫正极中，硫活性相、固态电解质、导电/催化组分的种类、比例和空间/界面安排，如何共同决定硫的可逆利用、离子/电子传输、固固接触和电解质副反应；如何据文献条件提出新的材料或组合，并在明确工况下公平验证？"]];
overview.getRange("A33:D33").format = { font: bodyFont, wrapText: true, verticalAlignment: "center" };
overview.getRange("A33").format = { fill: paleBlue, font: { name: font, size: 10, bold: true, color: "#202124" }, verticalAlignment: "center" };
overview.getRange("A33:D33").format.rowHeight = 68;
overview.getRange("A35:B38").values = [
  ["当前阶段", "全量摘要索引完成；主问题已定，配方待全文对照。"],
  ["数据是否够", "可支持筛选与抽样；摘要不能单独选定配方。"],
  ["下一停点", "全文统一抽取配比、结构、载量、压力、温度和电位。"],
  ["配方确定时点", "完成条件对照后定配方、强参照、机制对照和否定条件。"],
];
overview.getRange("A35:B38").format = { font: bodyFont, wrapText: true, verticalAlignment: "top" };
overview.getRange("A35:A38").format = { fill: paleBlue, font: { name: font, size: 10, bold: true, color: "#202124" }, verticalAlignment: "center" };
overview.getRange("A35:B38").format.rowHeight = 27;

overview.getRange("A40:B43").values = [
  ["固态锂硫引用来源体系的记录边数", "说明"],
  ["→ 固态锂电池", data.summary.target_citation_bridges.find((x) => x["来源体系"] === "固态锂电池")?.["固态锂硫引用记录数"] ?? 0],
  ["→ 液态锂硫", data.summary.target_citation_bridges.find((x) => x["来源体系"] === "液态锂硫")?.["固态锂硫引用记录数"] ?? 0],
  ["→ 准固态锂硫", data.summary.target_citation_bridges.find((x) => x["来源体系"] === "准固态锂硫")?.["固态锂硫引用记录数"] ?? 0],
];
styleHeader(overview, "A40:B40");
overview.getRange("B41:B43").format.numberFormat = "#,##0";
overview.getRange("A44:D44").values = [["口径", "", "", "这是引用表中的引用边条数，不是独立论文数，也不代表方案有效或引用质量。"]];
overview.getRange("A44:D44").format = { font: { name: font, size: 9, italic: true, color: "#666666" }, wrapText: false, verticalAlignment: "center" };
overview.getRange("A44:D44").format.rowHeight = 20;
overview.getRange("A46:D46").values = [["标签口径", "", "", "来源体系索引按各主题优先纳入固态锂硫引用较多和2022年后文献；准固态相关候选单独列出。摘要关键词用于找候选，效果和机制仍需回全文核实。"]];
overview.getRange("A46:D46").format = { font: { name: font, size: 9, italic: true, color: "#555555" }, wrapText: true, verticalAlignment: "top" };
overview.getRange("A46:D46").format.rowHeight = 42;
overview.getRange("A1:A46").format.columnWidth = 28;
overview.getRange("B1:B46").format.columnWidth = 32;
overview.getRange("C1:C46").format.columnWidth = 30;
overview.getRange("D1:D46").format.columnWidth = 62;
overview.getRange("A1").format.font = { name: font, size: 15, bold: true, color: "#1F1F1F" };
overview.getRange("A4:D4").format.rowHeight = 28;
overview.getRange("A10:C10").format.rowHeight = 28;
overview.getRange("A19:B19").format.rowHeight = 28;
overview.getRange("A27:D27").format.rowHeight = 30;

// Evidence strategy map: statements are based on abstracts unless marked as the
// previously checked full-text F set; each transfer row includes an explicit boundary.
styleTitle(strategies, "A1", "各体系已有方案、对固态锂硫的启示与迁移边界");
strategies.getRange("A2").values = [["代表例用于说明方案类型与检索方向；性能和条件以摘要信息为准，实验设计前还需回到全文/补充材料核验。"]];
strategies.getRange("A2").format = { font: { name: font, size: 10, italic: true, color: "#666666" }, wrapText: true };
const strategyRows = [
  ["体系", "方案类型", "代表文献编号 / 年份", "摘要中报告的做法与条件", "对固态锂硫的启示", "适用边界 / 需要核查"],
  ["固态锂硫", "正极—硫化物电解质界面改性", "W4386307881 / 2023", "在S8与Li6PS5Cl之间形成含多硫代中间体的离子导电界面；混料时用后续去除的弱极性溶剂促进界面反应；室温面容量5.1 mAh cm−2，报告250圈。", "用界面化学把电子绝缘硫与离子导体连接起来；界面组分、制程和位置可以与整体配方一起比较。", "需核全文中溶剂去除、含硫界面相比例、压力、载硫量和容量归属。"],
  ["固态锂硫", "碳宿主与单原子催化相组合", "W4376149270 / 2023", "乙炔黑负载Co–N4并球磨制备硫宿主；摘要报告4.5 mg cm−2硫载量下5.13 mAh cm−2，条件为60°C。", "新组合可以是‘碳网络×催化位点×配比/加工’，无需创造全新电池体系。", "温度、硫占比、球磨条件、运行压力、长循环容量和对照配方需全文核验。"],
  ["固态锂硫", "柔性导电网络与力学调节", "W4393342138 / 2024", "PPy包覆氮掺杂CNT形成弹性导电通道；摘要报告面载量4.5 mg cm−2、面容量6 mAh cm−2及运行中压力变化。", "碳相不只负责导电，也可缓冲体积变化和局部应力；要把电化学、接触和力学指标并列。", "核对PPy比例、网络结构、堆压控制方式、温度与对照组。"],
  ["固态锂硫", "分级碳结构构造三相界面", "W4404443684 / 2024", "层级碳纳米笼形成连续网络并限域纳米硫；摘要报告6 mg cm−2、40 wt%硫、60°C下9.95 mAh cm−2。", "材料组合与空间安排共同改变离子/电子路径和应力，可作为结构工程候选。", "高温结果不能直接当室温实用表现；需核对堆压、面容量与循环窗口。"],
  ["固态锂硫", "固态电解质密度/粒径/配比", "W4362635226 / 2023", "使用低密度Li3PS4–2LiBH4玻璃陶瓷；摘要报告60 wt%硫、约55 MPa平均堆压和60°C测试。", "电解质自身的密度、粒径和体积占比可能决定正极离子通道与惰性质量，可与碳比例共同优化。", "该研究压力较高；要核对真实硫面载量、压片与运行压力是否分开。"],
  ["固态锂硫", "调放电产物并加入微量LiI", "W4387569448 / 2023", "报告产物为Li2S2/Li2S混合物；通过下截止电位调成Li2S2占优，并在硫复合正极中加入微量LiI，25°C下长循环。", "截止电位、放电产物、催化添加剂和界面化学需作为联动变量，不能只比较添加剂名称。", "需区分LiI催化/介体机制、产物比例测定、容量来源和电解质消耗。"],
  ["液态锂硫", "原位生成并固定的多硫化物介体", "W1989121075 / 2015", "MnO2表面反应生成硫代硫酸盐型结合中间体，介导多硫化物转化并限制溶解；摘要还报告可延展至氧化石墨烯。", "可借鉴‘活性物种原位生成并固定在界面’的功能思路，评估其在固态正极中的位置与再生。", "液态中的溶解/穿梭条件不能照搬；需确认固态下离子可达性、电子隔离及副产物稳定性。"],
  ["固态锂金属相关", "追踪电解质—锂界面反应与阻抗演化", "W2294978050 / 2016", "LGPS与金属锂反应生成Li3P、Li2S和Li–Ge合金界面层，阻抗随界面反应增加。", "迁移‘先查界面反应产物与随时间的阻抗变化’，帮助筛查电解质/界面层组合。", "这是负极电位与锂金属界面，不能推断硫正极电位下的稳定性。"],
  ["固态电池综述", "界面层、涂层与力学接触设计", "W3038591351 / 2020（综述）", "综述把固固接触、界面化学、涂层、运行堆压和力学演化作为全固态电池关键变量。", "用作条件表和表征路线来源：记录界面成分/分布、离子/电子性质、压力与时间演化。", "综述是方法/概念来源，不是目标正极配方证据；必须返回实验论文确认。"],
];
strategies.getRangeByIndexes(3, 0, strategyRows.length, strategyRows[0].length).values = strategyRows;
styleHeader(strategies, "A4:F4");
addTable(strategies, `A4:F${3 + strategyRows.length}`, "StrategyTransferMap");
strategies.getRange(`A5:F${3 + strategyRows.length}`).format = { font: bodyFont, wrapText: true, verticalAlignment: "top" };
strategies.getRange(`A5:F${3 + strategyRows.length}`).format.rowHeight = 68;
strategies.getRange("A1:A20").format.columnWidth = 20;
strategies.getRange("B1:B20").format.columnWidth = 30;
strategies.getRange("C1:C20").format.columnWidth = 31;
strategies.getRange("D1:D20").format.columnWidth = 64;
strategies.getRange("E1:E20").format.columnWidth = 58;
strategies.getRange("F1:F20").format.columnWidth = 54;
strategies.freezePanes.freezeRows(4);

// Unified row-level index. The source group and retrieval tags remain explicit.
const headers = ["体系", "编号", "年份", "文献类型", "标题", "DOI", "主题标签", "摘要", "摘要可用", "被固态锂硫库引用篇数", "本地PDF登记路径", "电解质类型", "正极路线", "来源", "筛选边界", "纳入依据"];
const rows = [];
for (const r of data.solid_lis_records) {
  rows.push([
    "固态锂硫", safeText(r["编号"]), numericYear(r["年份"]), safeText(r["文献类型"]), safeText(r["标题"]), safeText(r["DOI"]),
    safeText(r["主题标签"]), safeText(r["摘要"]), safeText(r["摘要可用"]), Number(r["被固态锂硫库引用的篇数"] || 0), safeText(r["本地PDF登记路径"]),
    safeText(r["电解质类型"]), safeText(r["正极路线"]), safeText(r["来源"]), "主目标组；标签为题名+摘要检索线索", "主库全量，不抽样",
  ]);
}
for (const r of selectedTransferRecords) {
  let group = r["体系"];
  let boundary = "来源体系候选；标签为题名+摘要检索线索；不等于已证明可迁移";
  if (group === "固态锂金属/负极相关固态电池") {
    group = "固态锂电池（锂金属/负极相关）";
    boundary = "固态电池组内按锂金属/负极题名或摘要词筛选；与固态锂硫正极有边界差异";
  } else if (group === "准固态锂硫（边界对照）") {
    boundary = "边界对照；含液/准固态配方不并入全固态锂硫主库";
  }
  rows.push([
    safeText(group), safeText(r["编号"]), numericYear(r["年份"]), safeText(r["文献类型"]), safeText(r["标题"]), safeText(r["DOI"]),
    safeText(r["策略主题"]), safeText(r["摘要"]), "是", Number(r["被固态锂硫库引用的篇数"] || 0), "", "", "", safeText(r["来源"]), boundary,
    Array.from(selectedReasons.get(`${r["体系"]}|${r["编号"]}`) || []).join("；"),
  ]);
}
index.getRangeByIndexes(0, 0, rows.length + 1, headers.length).values = [headers, ...rows];
styleHeader(index, `A1:P1`);
addTable(index, `A1:P${rows.length + 1}`, "LiteratureIndex");
index.getRange(`A2:P${rows.length + 1}`).format = { font: bodyFont, verticalAlignment: "center", wrapText: false };
index.getRange(`C2:C${rows.length + 1}`).format.numberFormat = "0";
index.getRange(`J2:J${rows.length + 1}`).format.numberFormat = "#,##0";
for (const [col, width] of [["A",36],["B",16],["C",10],["D",19],["E",58],["F",28],["G",34],["H",78],["I",12],["J",20],["K",58],["L",20],["M",22],["N",13],["O",58],["P",48]]) {
  index.getRange(`${col}1:${col}${rows.length + 1}`).format.columnWidth = width;
}
index.freezePanes.freezeRows(1);
index.freezePanes.freezeColumns(2);

wb.recalculate();
const check = await wb.inspect({ kind: "table", sheetId: "候选判断", range: "A1:D46", include: "values", tableMaxRows: 46, tableMaxCols: 4, maxChars: 8000 });
console.log(check.ndjson);
const preview = await wb.render({ sheetName: "候选判断", range: "A1:D46", scale: 1, format: "png" });
await fs.writeFile(new URL("./preview.png", import.meta.url), new Uint8Array(await preview.arrayBuffer()));
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(outPath);
console.log(`EXPORTED ${outPath}; index rows=${rows.length}; target=${data.solid_lis_records.length}; transfer shortlist=${selectedTransferRecords.length}; full transfer candidate pool=${data.transfer_records.length}`);
