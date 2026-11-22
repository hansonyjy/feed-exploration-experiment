// Number formatting shared by all pages. Absolute changes come first, relative second (D61).

export function pp(x: number, digits = 1): string {
  const v = x * 100;
  const s = Math.abs(v).toFixed(digits);
  return `${v < 0 ? "−" : v > 0 ? "+" : ""}${s} pp`;
}

export function pct(x: number, digits = 0): string {
  const v = x * 100;
  const s = Math.abs(v).toFixed(digits);
  return `${v < 0 ? "−" : v > 0 ? "+" : ""}${s}%`;
}

export function share(x: number, digits = 3): string {
  return `${(x * 100).toFixed(digits)}%`;
}

// Decimals for a value in percentage points, matching the findings tables (34.6, 1.94, 0.323, 0.058).
export function sig(ppValue: number): number {
  const a = Math.abs(ppValue);
  return a >= 10 ? 1 : a >= 1 ? 2 : 3;
}
