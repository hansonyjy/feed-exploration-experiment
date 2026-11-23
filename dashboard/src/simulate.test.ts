import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { parsePage, type RawPage, type Row } from "./data";
import {
  GUARDRAILS,
  PREREG_LIMIT,
  SHARE_MAX,
  SHARE_MIN,
  binding,
  costsPer1000,
  guardrailChange,
  intervalCrossesLimit,
  recommendedShare,
  status,
} from "./simulate";

const raw = JSON.parse(readFileSync(new URL("../../exports/dashboard/budget.json", import.meta.url), "utf-8")) as RawPage;
const page = parsePage(raw);
const rows = page.tables.budget;
const estimates = new Map(page.tables.budget_estimates.map((e) => [`${e.dimension}/${e.segment}`, e]));
const name = (r: Row) => `${r.dimension}/${r.segment}`;
const close = (a: number, b: number) => expect(Math.abs(a - b)).toBeLessThan(1e-12);

describe("simulator matches exploration_budget_prod.csv", () => {
  it("has every budget row", () => expect(rows.length).toBe(45));

  for (const r of rows) {
    it(`${name(r)}: guardrail changes at 0.658% and 1.388%`, () => {
      for (const g of GUARDRAILS) {
        close(guardrailChange(r, g, SHARE_MIN).relative, r[`${g}_feed_change_at_low`] as number);
        const hi = guardrailChange(r, g, SHARE_MAX);
        close(hi.relative, r[`${g}_feed_change_at_high`] as number);
        close(hi.relativeLow, r[`${g}_feed_change_at_high_ci_low`] as number);
        close(hi.relativeHigh, r[`${g}_feed_change_at_high_ci_high`] as number);
        expect(intervalCrossesLimit(r, g, PREREG_LIMIT)).toBe(r[`${g}_interval_crosses_limit`]);
      }
    });

    it(`${name(r)}: binding share and guardrail`, () => {
      const exported = r.recommended_share as number | null;
      const ours = recommendedShare(r, PREREG_LIMIT);
      if (exported === null) expect(ours).toBeNull();
      else expect(Math.abs((ours as number) - exported)).toBeLessThan(1e-12);
      const b = binding(r, PREREG_LIMIT);
      expect(b.inRange ? b.guardrail : "none in range").toBe(r.binding_guardrail);
    });

    it(`${name(r)}: costs per 1,000 impressions at the exported share`, () => {
      const share = r.recommended_share as number | null;
      const e = estimates.get(name(r))!;
      expect(e).toBeDefined();
      if (share === null) return; // dance: no exported share, so the export has no cost to compare
      const c = costsPer1000(e, share);
      close(c.effectiveView, r.effective_view_change_per_1000_impressions as number);
      close(c.newAuthorFollow, r.new_author_follow_change_per_1000_impressions as number);
      close(c.newCategoryEffectiveView, r.new_category_effective_view_change_per_1000_impressions as number);
    });
  }

  it("classifies segments as in findings.md: dance actionable, six on the watch list, the rest clear", () => {
    const segs = rows.filter((r) => r.dimension !== "overall");
    const by = (s: string) => segs.filter((r) => status(r, PREREG_LIMIT) === s).map(name).sort();
    expect(by("actionable")).toEqual(["category_segment/1"]);
    expect(by("watch")).toEqual(
      ["activity_tercile/2", "category_segment/15", "category_segment/2", "category_segment/20", "category_segment/32", "tenure_band/181-365"].sort(),
    );
    expect(by("none").length).toBe(37);
    expect(status(rows.find((r) => r.dimension === "overall")!, PREREG_LIMIT)).toBe("none");
  });
});
