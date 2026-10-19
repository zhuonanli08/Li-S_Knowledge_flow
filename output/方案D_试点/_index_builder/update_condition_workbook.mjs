import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const root='D:/Desktop/课题一锂硫知识流动分析/output/方案D_试点';
const data=JSON.parse(await fs.readFile(`${root}/_index_builder/condition_review_data.json`,'utf8'));
const path=`${root}/全库文献索引.xlsx`;
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(path));
const s=wb.worksheets.getItem('候选判断');
s.getRange('D2').values=[['主问题明确；10篇条件核查完成，首轮四组配方已提出（待验证）。']];
s.getRange('D2').format.wrapText=true;s.getRange('A2:D2').format.rowHeight=40;
s.getRange('D33').values=[['怎样搭配促进硫转化的电解质/功能相与能保持接触的导电网络，使高载硫正极兼顾可逆利用、稳定循环和电解质副反应控制？材料、配比、组合和加工均可优化。']];
s.getRange('A35:B38').values=[['当前阶段','10篇条件/机制核查；11条记录；23处原文定位。'],['数据是否够','足以提出可检验的主问题；不足以认定最优配方或首次创新。'],['第一轮候选','E0/E1 × 有/无5 wt% PPy@NCNT；详见配方候选。'],['下一步','补查相容性和补充材料，复现基准后做公平对照。']];
s.getRange('A35:B38').format.rowHeight=56;
function table(name,headers,rows,widths){const sh=wb.worksheets.add(name);sh.showGridLines=false;sh.getRangeByIndexes(0,0,rows.length+1,headers.length).values=[headers,...rows];const r=sh.getRangeByIndexes(0,0,rows.length+1,headers.length);r.format={font:{name:'Arial',size:10,color:'#202124'},wrapText:true,verticalAlignment:'top'};sh.getRangeByIndexes(0,0,1,headers.length).format={fill:'#1F4E78',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,verticalAlignment:'center',rowHeight:34};sh.getRangeByIndexes(1,0,rows.length,headers.length).format.rowHeight=108;widths.forEach((w,i)=>{sh.getRangeByIndexes(0,i,rows.length+1,1).format.columnWidth=w;});const t=sh.tables.add(sh.getRangeByIndexes(0,0,rows.length+1,headers.length).address,true,name==='全文条件对照'?'FulltextConditions':name==='配方候选'?'RecipeCandidates':'TransferBasis');t.style='TableStyleMedium2';sh.freezePanes.freezeRows(1);return sh;}
table('全文条件对照',data.headers,data.rows,[19,28,56,18,34,17,20,31,38,48,48,52,19,35]);
const recipes=table('配方候选',[...data.recipe_headers,'合计 (wt%)'],data.recipes.map(r=>[...r,null]),[14,25,24,14,14,17,20,18,23,66,17]);
data.recipes.forEach((r,i)=>{recipes.getRange(`K${i+2}`).formulas=[[`=SUM(D${i+2}:I${i+2})`]];});
recipes.getRange('D2:K6').format.numberFormat='0';
recipes.getRange('A8:C15').values=[['定义','组成 / 要点','状态'],['E0','Li10.5Si1.5P1.5S12','名义组成；不是惰性对照'],['E1','Li10.1Si1.5P1.5S11.6I0.4','名义多相材料'],['PPy@NCNT','聚吡咯包覆的氮掺杂碳纳米管','网络功能；不自动等同介体'],['统一条件','拟定5 mg S/cm²、45°C、12.5/5 MPa独立启动','相同隔层、负极和电位窗口；兼容性先核'],['样本建议','4组×2压力×3独立电池＝24只','不含复现、无硫和后续机制对照'],['创新边界','原文已建议聚合物；具体组合需查新和证实','不是已经确认的新颖性或最优配方'],['电解质隔层','建议固定E0并先查界面兼容性','固定隔层的R10是改造参照']];
recipes.getRange('A8:C15').format={wrapText:true,font:{name:'Arial',size:10},rowHeight:72,verticalAlignment:'top'};
const sourceRows=data.sources.map(r=>[r['编号'],r['分组'],Number(r['年份']),r['标题'],r['DOI'],'来源例证：题录/摘要依据，未计入本轮10篇全文条件核查']);
table('来源策略依据',['编号','来源体系','年份','题名','DOI','证据深度'],sourceRows,[20,22,13,80,37,62]);
wb.recalculate();
const totals=recipes.getRange('K2:K6').values;if(totals.some(r=>r[0]!==100))throw new Error(`bad recipe totals ${JSON.stringify(totals)}`);
const ids=wb.worksheets.getItem('文献索引').getRange('A2:A1782').values;if(ids.filter(r=>r[0]!=null&&r[0]!=='').length!==1781)throw new Error('Index row count changed');
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20}});console.log(JSON.stringify({totals,indexRows:1781,errors}));
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(path);
for(const [sheetName,range,file] of [['配方候选','A1:K6','recipe_preview'],['全文条件对照','A1:G5','conditions_preview'],['候选判断','A27:D38','decision_preview']]){const preview=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(`${root}/_index_builder/${file}.png`,new Uint8Array(await preview.arrayBuffer()));}
console.log(JSON.stringify({saved:path,sheets:6,conditionRows:data.rows.length}));
