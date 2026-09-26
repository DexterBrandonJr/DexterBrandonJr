import "server-only";

// Neutralizes CSV formula injection: a cell starting with =, +, -, @, or a
// tab/CR can be interpreted as a formula by Excel/Sheets when the export is
// later opened. Prefixing with an apostrophe forces it to be read as text.
const FORMULA_TRIGGER = /^[=+\-@\t\r]/;

export function toCsvField(value: unknown): string {
  let str = value === null || value === undefined ? "" : String(value);
  if (FORMULA_TRIGGER.test(str)) {
    str = `'${str}`;
  }
  if (/[",\n\r]/.test(str)) {
    str = `"${str.replaceAll('"', '""')}"`;
  }
  return str;
}

export function toCsvRow(values: unknown[]): string {
  return values.map(toCsvField).join(",");
}

export function toCsv(header: string[], rows: unknown[][]): string {
  return [toCsvRow(header), ...rows.map(toCsvRow)].join("\r\n") + "\r\n";
}
