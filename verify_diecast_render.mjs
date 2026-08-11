import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbookPath = "outputs/wiki_audit/Diecast 2026 - doplneno z auditu - body 1976-2025.xlsx";
const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const overview = await workbook.inspect({
  kind: "workbook,sheet,region",
  sheetId: "Overview",
  range: "A1957:P1982",
  tableMaxRows: 8,
  tableMaxCols: 16,
  maxChars: 4000,
});
console.log(overview.ndjson);

const preview = await workbook.render({
  sheetName: "Overview",
  range: "A1957:P1982",
  scale: 1,
  format: "png",
});
await fs.writeFile(
  "outputs/wiki_audit/diecast_standings_preview.png",
  new Uint8Array(await preview.arrayBuffer()),
);
