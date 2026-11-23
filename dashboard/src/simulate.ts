// Exploration-budget simulator (D48, D57, D59, D61). Pure functions over one row of
// exports/exploration_budget_prod.csv (via budget.json); no data is fetched or invented here.
//
// Linear within the observed range, as in D48: at exploration share s, a guardrail's feed-level
// relative change is s x (the segment's relative effect of a random slot), and its interval is
// s x [relative low, relative high]. Absolute change = recommended baseline x that relative change.
// Costs per 1,000 impressions are share x the segment's per-impression estimate x 1,000.

import type { Row } from "./data";

export const SHARE_MIN = 0.00658; // lowest share of tab-1 exposures that are random, in the data
export const SHARE_MAX = 0.01388; // highest share in the data; nothing above it was observed
export const PREREG_LIMIT = 0.02; // a guardrail may worsen by at most 2% relative (pre-registered)

export type Guardrail = "hate" | "fast_skip";
export const GUARDRAILS: Guardrail[] = ["hate", "fast_skip"];

function n(row: Row, col: string): number {
  const v = row[col];
  if (typeof v !== "number") throw new Error(`${col} is not a number`);
  return v;
}

export interface Change {
  relative: number; // feed-level relative change at share s
  relativeLow: number;
  relativeHigh: number;
  absolute: number; // change in the feed's rate, as a fraction (x100 for pp)
  absoluteLow: number;
  absoluteHigh: number;
  baseline: number;
}

export function guardrailChange(row: Row, g: Guardrail, share: number): Change {
  const base = n(row, `${g}_baseline`);
  const [rel, lo, hi] = ["rel_effect", "rel_low", "rel_high"].map((c) => share * n(row, `${g}_${c}`));
  return { relative: rel, relativeLow: lo, relativeHigh: hi, absolute: base * rel, absoluteLow: base * lo, absoluteHigh: base * hi, baseline: base };
}

export interface Costs {
  effectiveView: number;
  newAuthorFollow: number;
  newCategoryEffectiveView: number;
}

// Change per 1,000 tab-1 impressions at share s (negative = fewer), from the segment's
// per-impression Comparison A estimates (budget_estimates): s x estimate x 1,000, as in exploration_budget.py.
export function costsPer1000(estimates: Row, share: number): Costs {
  const k = share * 1000;
  return {
    effectiveView: k * n(estimates, "effective_view_estimate"),
    newAuthorFollow: k * n(estimates, "new_author_follow_estimate"),
    newCategoryEffectiveView: k * n(estimates, "new_category_effective_view_estimate"),
  };
}

export interface Binding {
  guardrail: Guardrail | null; // the first guardrail to reach the limit, or null if none rises
  share: number | null; // the share where it reaches the limit (point estimate), if it rises
  inRange: boolean; // reaches the limit at or below the top of the observed range
  belowRange: boolean; // already past the limit at the lowest share in the data
}

export function binding(row: Row, limit: number): Binding {
  let best: { g: Guardrail; s: number } | null = null;
  for (const g of GUARDRAILS) {
    const rel = n(row, `${g}_rel_effect`);
    if (rel <= 0) continue;
    const s = limit / rel;
    if (!best || s < best.s) best = { g, s };
  }
  if (!best) return { guardrail: null, share: null, inRange: false, belowRange: false };
  return { guardrail: best.g, share: best.s, inRange: best.s <= SHARE_MAX, belowRange: best.s < SHARE_MIN };
}

// The export's recommended share: the binding share capped at the top of the range, or null when
// the guardrail is already past the limit at the lowest share in the data (D48).
export function recommendedShare(row: Row, limit: number): number | null {
  const b = binding(row, limit);
  if (!b.inRange) return SHARE_MAX;
  return b.belowRange ? null : b.share;
}

// D59 flag: the limit lies inside the guardrail's interval somewhere in the observed range.
export function intervalCrossesLimit(row: Row, g: Guardrail, limit: number): boolean {
  return SHARE_MIN * n(row, `${g}_rel_low`) <= limit && limit <= SHARE_MAX * n(row, `${g}_rel_high`);
}

export type Status = "actionable" | "watch" | "none";

// actionable: even the interval's lower bound reaches the limit within the observed range, so the
//   guardrail binds there with confidence (dance at the pre-registered 2%).
// watch: the point estimate reaches the limit within the range, but the interval is too wide to say.
// none: no guardrail reaches the limit up to the top of the range.
export function status(row: Row, limit: number): Status {
  const b = binding(row, limit);
  if (!b.inRange || !b.guardrail) return "none";
  return SHARE_MAX * n(row, `${b.guardrail}_rel_low`) >= limit ? "actionable" : "watch";
}
