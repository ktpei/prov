const SHORT_NAMES: Record<string, string> = {
  "cloudflare-q3-2024-release": "Q3 release",
  "cloudflare-q3-2024-filing": "10-Q",
  "cloudflare-q3-2024-transcript": "Call transcript",
  "cloudflare-investor-day-2024": "Investor Day deck",
  "aapl-fy2024": "Apple FY24 Q4",
  "msft-fy2025-q1": "Microsoft FY25 Q1",
  "nvda-fy2025-q3": "NVIDIA FY25 Q3",
  "amzn-2024-q3": "Amazon Q3 2024",
  "meta-2024-q3": "Meta Q3 2024",
};

export function shortSource(id: string, title?: string): string {
  if (id.startsWith("workbook:")) return "Workbook";
  return SHORT_NAMES[id] ?? title ?? id;
}

const UPPER = new Set(["gaap", "eps", "yoy", "fcf", "rpo", "aws", "us", "usd", "ceo", "cfo"]);

export function humanizeKey(key: string): string {
  const words = key.split(/[_\s]+/).filter(Boolean);
  return words
    .map((word, index) => {
      const lower = word.toLowerCase();
      if (UPPER.has(lower)) return lower.toUpperCase();
      if (/^(fy|q)\d/.test(lower)) return lower.toUpperCase();
      if (lower === "non" && words[index + 1]?.toLowerCase() === "gaap") return "Non";
      return index === 0 ? lower.charAt(0).toUpperCase() + lower.slice(1) : lower;
    })
    .join(" ")
    .replace(/Non GAAP/g, "Non-GAAP")
    .replace(/non GAAP/g, "non-GAAP");
}

const numberFormat = new Intl.NumberFormat("en-US", { maximumFractionDigits: 6 });

export function formatValue(value: number | string, unit: string): string {
  if (typeof value === "string") return value;
  const lowered = unit.toLowerCase();
  if (lowered === "percent" || lowered === "%") return `${numberFormat.format(value)}%`;
  return numberFormat.format(value);
}

export function formatUnit(unit: string): string {
  const lowered = unit.trim().toLowerCase();
  return ["qualitative", "percent", "%"].includes(lowered) ? "" : unit;
}

export function money(value: number | null | undefined, digits = 4): string {
  if (value === null || value === undefined) return "—";
  return `$${value.toFixed(digits)}`;
}

export function lineRange(locator: string): [number, number] | null {
  const match = /^L(\d+)(?:-L?(\d+))?$/.exec(locator.trim());
  if (!match) return null;
  const start = Number(match[1]);
  return [start, Number(match[2] ?? match[1])];
}

export function columnLetter(column: number): string {
  let label = "";
  let n = column;
  while (n > 0) {
    const remainder = (n - 1) % 26;
    label = String.fromCharCode(65 + remainder) + label;
    n = Math.floor((n - 1) / 26);
  }
  return label;
}

function columnNumber(letters: string): number {
  return [...letters.toUpperCase()].reduce((total, letter) => total * 26 + letter.charCodeAt(0) - 64, 0);
}

export type CellRange = { sheet: string; r1: number; c1: number; r2: number; c2: number };

export function parseCellLocator(locator: string, fallbackSheet = ""): CellRange | null {
  const bang = locator.lastIndexOf("!");
  const sheet = bang >= 0 ? locator.slice(0, bang).replace(/^'(.*)'$/, "$1") : fallbackSheet;
  const parts = (bang >= 0 ? locator.slice(bang + 1) : locator).split(":");
  const points = parts.map((part) => /^\$?([A-Za-z]{1,3})\$?(\d+)$/.exec(part.trim()));
  if (points.length < 1 || points.length > 2 || points.some((point) => !point)) return null;
  const [first, last] = [points[0]!, points[points.length - 1]!];
  if (Number(first[2]) < 1 || Number(last[2]) > 1048576 ||
      columnNumber(last[1]) > 16384 || Number(last[2]) < Number(first[2]) ||
      columnNumber(last[1]) < columnNumber(first[1])) return null;
  return {
    sheet,
    r1: Number(first[2]),
    c1: columnNumber(first[1]),
    r2: Number(last[2]),
    c2: columnNumber(last[1]),
  };
}

export function rangeLabel(range: { r1: number; c1: number; r2: number; c2: number }): string {
  const r1 = Math.min(range.r1, range.r2);
  const r2 = Math.max(range.r1, range.r2);
  const c1 = Math.min(range.c1, range.c2);
  const c2 = Math.max(range.c1, range.c2);
  const start = `${columnLetter(c1)}${r1}`;
  const end = `${columnLetter(c2)}${r2}`;
  return start === end ? start : `${start}:${end}`;
}

const REASONS: Record<string, string> = {
  model_call_limit: "The agent used all 8 model steps before producing a cited answer.",
  tool_call_limit: "The agent used all 10 tool calls before producing a cited answer.",
  wall_clock_limit: "The 120-second time limit was reached.",
  spend_limit: "The per-question spend limit was reached.",
  input_size_limit: "The evidence gathered grew past the context limit.",
  worker_crashed: "The research process stopped unexpectedly.",
  worker_timeout: "The research process did not finish in time and was stopped.",
};

export function explainReason(reason: string | null): string {
  if (!reason) return "The run ended without a validated answer.";
  return REASONS[reason] ?? reason;
}
