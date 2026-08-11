import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const baseDir = process.cwd();
const outDir = path.join(baseDir, "outputs", "model_catalog");
const dataPath = path.join(outDir, "all_f1_143_models_matched.json");
const summaryPath = path.join(outDir, "all_f1_143_models_summary.json");
const outputPath = path.join(outDir, "All known F1 1-43 models - expanded clean matched to collection.xlsx");

const rows = JSON.parse(await fs.readFile(dataPath, "utf8"));
const summary = JSON.parse(await fs.readFile(summaryPath, "utf8"));

function colLetter(n) {
  let s = "";
  n += 1;
  while (n > 0) {
    const mod = (n - 1) % 26;
    s = String.fromCharCode(65 + mod) + s;
    n = Math.floor((n - mod) / 26);
  }
  return s;
}

function writeTable(sheet, startRow, startCol, headers, data, tableName) {
  const matrix = [headers, ...data.map((row) => headers.map((h) => row[h] ?? ""))];
  const range = sheet.getRangeByIndexes(startRow, startCol, matrix.length, headers.length);
  range.values = matrix;
  const address = `${colLetter(startCol)}${startRow + 1}:${colLetter(startCol + headers.length - 1)}${startRow + matrix.length}`;
  const table = sheet.tables.add(address, true, tableName);
  table.showFilterButton = true;
  table.showBandedRows = true;
  const headerRange = sheet.getRangeByIndexes(startRow, startCol, 1, headers.length);
  headerRange.format = {
    fill: "#1F4E78",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
  };
  range.format.borders = { preset: "outside", style: "thin", color: "#B7C9D8" };
  return range;
}

function countRows(counter) {
  return Object.entries(counter)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([name, count]) => ({ Name: name, Count: count }));
}

const workbook = Workbook.create();

const summarySheet = workbook.worksheets.add("Summary");
summarySheet.showGridLines = false;
summarySheet.getRange("A1:E1").merge();
summarySheet.getRange("A1").values = [["All known/sourced F1 1/43 models"]];
summarySheet.getRange("A1").format = {
  fill: "#16324F",
  font: { bold: true, color: "#FFFFFF", size: 16 },
};
summarySheet.getRange("A3:B8").values = [
  ["Total sourced model rows", summary.total_models],
  ["Exact code matches owned", summary.by_match_status["VlastnÄ›no - pĹ™esnĂ˝ kĂłd"] ?? 0],
  ["Likely owned matches", summary.by_match_status["VlastnÄ›no - pravdÄ›podobnĂˇ shoda"] ?? 0],
  ["Possible owned matches", summary.by_match_status["MoĹľnĂˇ shoda ve sbĂ­rce"] ?? 0],
  ["Not found in collection", summary.by_match_status["Nenalezeno ve sbĂ­rce"] ?? 0],
  ["Primary scale", "1/43"],
];
summarySheet.getRange("A3:B8").format.borders = { preset: "outside", style: "thin", color: "#B7C9D8" };
summarySheet.getRange("A3:A8").format = { fill: "#D9EAF7", font: { bold: true } };
summarySheet.getRange("B3:B8").format.numberFormat = "#,##0";
summarySheet.getRange("A10:E11").merge();
summarySheet.getRange("A10").values = [["Scope note: The catalogue is sourced from public manufacturer, retailer, and archive pages. It is broad and auditable, but not guaranteed to be a complete global production registry."]];
summarySheet.getRange("A10:E11").format = { fill: "#FFF2CC", wrapText: true };

const statusRows = countRows(summary.by_match_status);
writeTable(summarySheet, 12, 0, ["Name", "Count"], statusRows, "SummaryMatchStatus");
const manufacturerRows = countRows(summary.by_manufacturer);
writeTable(summarySheet, 12, 3, ["Name", "Count"], manufacturerRows, "SummaryManufacturer");
summarySheet.getRange("A1:M35").format.autofitColumns();

const allSheet = workbook.worksheets.add("All sourced models");
allSheet.showGridLines = false;
const headers = [
  "Year",
  "Constructor/Car",
  "Chassis/Type",
  "Driver",
  "Car number",
  "Team/livery",
  "Race/GP/version",
  "Manufacturer",
  "Model code",
  "Scale",
  "Source URL",
  "Match status against collection",
  "Collection Pc",
  "Collection row",
  "Collection Code",
  "Collection Driver",
  "Collection Car",
  "Collection Type",
  "Collection Extra",
  "Match score",
  "Source name",
  "Raw source title",
  "Limited edition",
  "Price AUD",
  "Notes",
];
writeTable(allSheet, 0, 0, headers, rows, "AllSourcedModels");
allSheet.freezePanes.freezeRows(1);
allSheet.getRange("A:A").format.numberFormat = "0";
allSheet.getRange("M:N").format.numberFormat = "0";
allSheet.getRange("T:T").format.numberFormat = "0";
allSheet.getRange("X:X").format.numberFormat = "#,##0.00";
allSheet.getRange("A1:Y50").format.autofitColumns();
const widths = [9, 20, 18, 20, 11, 18, 28, 16, 16, 8, 44, 32, 12, 12, 22, 20, 18, 16, 28, 11, 24, 56, 14, 12, 20];
for (let i = 0; i < widths.length; i++) {
  allSheet.getRange(`${colLetter(i)}:${colLetter(i)}`).format.columnWidth = widths[i];
}
allSheet.getRange("K:V").format.wrapText = true;

const byManufacturer = workbook.worksheets.add("By manufacturer");
byManufacturer.showGridLines = false;
writeTable(byManufacturer, 0, 0, ["Name", "Count"], manufacturerRows, "ByManufacturer");
byManufacturer.freezePanes.freezeRows(1);
byManufacturer.getRange("A:B").format.autofitColumns();

const byStatus = workbook.worksheets.add("By match status");
byStatus.showGridLines = false;
writeTable(byStatus, 0, 0, ["Name", "Count"], statusRows, "ByMatchStatus");
byStatus.freezePanes.freezeRows(1);
byStatus.getRange("A:B").format.autofitColumns();

const sources = workbook.worksheets.add("Sources");
sources.showGridLines = false;
const sourceRows = countRows(summary.by_source).map((row) => ({
  Source: row.Name,
  Rows: row.Count,
  URL:
    row.Name === "F1 Scale Models stock list"
      ? "https://www.f1scalemodels.com/F1_Stocklist.pdf"
      : row.Name === "143diecastmodels Minichamps pages"
        ? "http://www.143diecastmodels.co.uk/"
        : "https://looksmartmodels.com/product-tag/formula-1/",
}));
writeTable(sources, 0, 0, ["Source", "Rows", "URL"], sourceRows, "CatalogSources");
sources.getRange("A:C").format.autofitColumns();
sources.getRange("C:C").format.columnWidth = 58;

await fs.mkdir(outDir, { recursive: true });

const checks = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(checks.ndjson);

for (const sheetName of ["Summary", "All sourced models", "By manufacturer", "By match status", "Sources"]) {
  const previewRange = sheetName === "All sourced models" ? "A1:H30" : "A1:L35";
  const preview = await workbook.render({ sheetName, range: previewRange, scale: 1, format: "png" });
  await fs.writeFile(path.join(outDir, `${sheetName.replaceAll(" ", "_")}_preview.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
process.exit(0);

