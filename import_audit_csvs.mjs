import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = path.resolve("outputs", "wiki_audit");
const targetPath = path.join(outputDir, "Audit souboru Diecast 2026.xlsx");

const imports = [
  ["yearly_summary.csv", "yearly_summary"],
  ["missing_in_sheet.csv", "missing_in_sheet"],
  ["extra_in_sheet.csv", "extra_in_sheet"],
  ["review_low_confidence.csv", "review_low_confidence"],
  ["order_issues.csv", "order_issues"],
  ["sources.csv", "sources"],
];

function colName(index) {
  let n = index + 1;
  let s = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    s = String.fromCharCode(65 + rem) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (inQuotes) {
      if (ch === '"' && next === '"') {
        field += '"';
        i += 1;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (ch !== "\r") {
      field += ch;
    }
  }
  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

function coerce(value) {
  if (value === "") return null;
  if (/^-?\d+(\.\d+)?$/.test(value) && !/^0\d/.test(value)) {
    const n = Number(value);
    if (Number.isFinite(n)) return n;
  }
  return value;
}

const workbook = Workbook.create();

for (const [csvName, sheetName] of imports) {
  const csvPath = path.join(outputDir, csvName);
  const text = await fs.readFile(csvPath, "utf8");
  const parsed = parseCsv(text.replace(/^\uFEFF/, ""));
  const rows = parsed.map((r) => r.map(coerce));
  const width = Math.max(...rows.map((r) => r.length), 1);
  const matrix = rows.map((r) => r.concat(Array(width - r.length).fill(null)));

  const sheet = workbook.worksheets.add(sheetName);
  const lastCol = colName(width - 1);
  const range = sheet.getRange(`A1:${lastCol}${matrix.length}`);
  range.values = matrix;

  const header = sheet.getRange(`A1:${lastCol}1`);
  header.format = {
    fill: "#1F4E78",
    font: { bold: true, color: "#FFFFFF" },
  };
  sheet.freezePanes.freezeRows(1);
  sheet.getRange(`A1:${lastCol}${matrix.length}`).format.wrapText = false;
  range.format.autofitColumns();
  range.format.autofitRows();
}

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(targetPath);

console.log(`Saved ${targetPath}`);
