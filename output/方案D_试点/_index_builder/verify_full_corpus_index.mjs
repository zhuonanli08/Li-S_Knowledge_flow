import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
const path = "D:/Desktop/课题一锂硫知识流动分析/output/方案D_试点/全库文献索引.xlsx";
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(path));
const sheets = await wb.inspect({ kind: "sheet", include: "id,name", maxChars: 3000 });
console.log(sheets.ndjson);
for (const [sheetName, range, file] of [
  ["方案对照", "A1:F13", "strategy_preview.png"],
  ["文献索引", "A1:P12", "index_preview.png"],
]) {
  const preview = await wb.render({ sheetName, range, scale: 1, format: "png" });
  await fs.writeFile(new URL(`./${file}`, import.meta.url), new Uint8Array(await preview.arrayBuffer()));
  const check = await wb.inspect({ kind: "table", sheetId: sheetName, range, include: "values", tableMaxRows: 12, tableMaxCols: 16, maxChars: 3000 });
  console.log(check.ndjson);
}
