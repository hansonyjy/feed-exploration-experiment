import * as Plot from "@observablehq/plot";
import { num, type Row } from "../data";
import { pct, share as fmtShare } from "../format";
import {
  PREREG_LIMIT,
  SHARE_MAX,
  SHARE_MIN,
  binding,
  costsPer1000,
  guardrailChange,
  status,
  type Change,
  type Guardrail,
  type Status,
} from "../simulate";
import { el } from "../ui";
import type { Data, Page } from "./page";

// Every input comes from budget.json (budget, budget_estimates, category_labels, budget_facts);
// the browser applies the linear rule in simulate.ts, which Vitest checks against the export.

const DIMENSIONS: { key: string; group: string }[] = [
  { key: "overall", group: "Whole feed" },
  { key: "category_segment", group: "Content: category of the random video" },
  { key: "duration_bucket", group: "Content: length of the random video" },
  { key: "activity_tercile", group: "Users: activity before the test" },
  { key: "active_group", group: "Users: activity group" },
  { key: "tenure_band", group: "Users: account age" },
  { key: "follow_band", group: "Users: accounts followed" },
];

const USER_LABELS: Record<string, string> = {
  "activity_tercile/no_pre_period+1": "Activity tercile 1 or no history",
  "activity_tercile/2": "Activity tercile 2",
  "activity_tercile/3": "Activity tercile 3 (most active)",
  "active_group/full_active": "Full-active users",
  "active_group/high_active": "High-active users",
  "active_group/new_or_low+middle_active": "New, low or middle-active users",
  "tenure_band/8-14 to 91-180": "Account age 8 to 180 days",
  "tenure_band/181-365": "Account age 181 to 365 days",
  "tenure_band/366-730": "Account age 366 to 730 days",
  "tenure_band/730+": "Account age over 730 days",
  "follow_band/0 to (0,10]": "Follows 0 to 10 accounts",
  "follow_band/(10,50]": "Follows 11 to 50 accounts",
  "follow_band/(50,100]": "Follows 51 to 100 accounts",
  "follow_band/(100,150]": "Follows 101 to 150 accounts",
  "follow_band/(150,250]": "Follows 151 to 250 accounts",
  "follow_band/(250,500]": "Follows 251 to 500 accounts",
  "follow_band/500+": "Follows over 500 accounts",
};

const STATUS_TEXT: Record<Status, { badge: string; detail: string }> = {
  actionable: { badge: "Actionable", detail: "The guardrail crosses the limit inside the observed range, even at the low end of its interval. Limit exploration here." },
  watch: { badge: "Watch list", detail: "The point estimate crosses the limit inside the observed range, but the interval is too wide to say. Watch it in the next test." },
  none: { badge: "No binding", detail: "No guardrail crosses the limit up to 1.388%, the highest share in the data." },
};

function key(r: Row): string {
  return `${r.dimension}/${r.segment}`;
}

function labeler(data: Data): (r: Row) => string {
  const cats = new Map(data.tables.category_labels.map((c) => [String(c.category_segment), String(c.label_en)]));
  return (r: Row) => {
    const seg = String(r.segment);
    if (r.dimension === "overall") return "Whole feed";
    if (r.dimension === "category_segment") return seg.includes("+") ? `Merged categories ${seg}` : cats.get(seg) ?? seg;
    if (r.dimension === "duration_bucket") return `Length decile ${seg.replace("+", " and ")}`;
    return USER_LABELS[key(r)] ?? seg;
  };
}

// Percentage points with enough digits for rare events (hate changes are around 0.001 pp).
function ppFine(x: number, signed = true): string {
  const v = x * 100;
  const a = Math.abs(v);
  const s = a >= 1 ? a.toFixed(2) : a >= 0.1 ? a.toFixed(3) : a === 0 ? "0" : a.toPrecision(2);
  return `${signed ? (v < 0 ? "−" : "+") : ""}${s} pp`;
}

function pctFine(x: number): string {
  const v = x * 100;
  return `${v < 0 ? "−" : "+"}${Math.abs(v).toFixed(2)}%`;
}

function per1000(x: number): string {
  const a = Math.abs(x);
  return `${x < 0 ? "−" : "+"}${a >= 1 ? a.toFixed(1) : a.toFixed(3)}`;
}

function guardrailRow(name: string, c: Change, limit: number): HTMLElement {
  const over = c.relative > limit;
  const cell = (main: string, ci: string) =>
    el("td", { class: "num" }, el("span", { class: "delta" }, main), el("span", { class: "ci-text cell-ci" }, ci));
  return el(
    "tr",
    { class: over ? "bad" : "" },
    el("th", { scope: "row", class: "c-metric" }, name),
    cell(ppFine(c.absolute), `${ppFine(c.absoluteLow)} to ${ppFine(c.absoluteHigh)}`),
    cell(pctFine(c.relative), `${pctFine(c.relativeLow)} to ${pctFine(c.relativeHigh)}`),
    el("td", { class: "num" }, el("span", {}, `${(limit * 100).toFixed(1)}%`), el("span", { class: "ci-text cell-ci" }, ppFine(limit * c.baseline, false))),
  );
}

function overview(rows: Row[], label: (r: Row) => string, limit: number, selected: string, width: number): Element {
  const pts = rows
    .map((r) => {
      const c = guardrailChange(r, "hate", SHARE_MAX);
      return { key: key(r), label: label(r), value: c.relative, low: c.relativeLow, high: c.relativeHigh, status: status(r, limit) };
    })
    .sort((a, b) => b.value - a.value);
  const narrow = width < 600;
  const color = (p: { status: Status }) => (p.status === "none" ? "var(--ink-2)" : "var(--bad)");
  const maxX = Math.max(limit, ...pts.map((p) => p.high)) * 1.05;
  return Plot.plot({
    width,
    height: pts.length * 17 + 40,
    marginLeft: narrow ? 150 : 230,
    marginRight: 16,
    marginTop: 24,
    style: { fontFamily: "var(--sans)", fontSize: narrow ? "11px" : "12px" },
    x: { domain: [Math.min(0, ...pts.map((p) => p.low)), maxX], label: null, tickFormat: (d: number) => pct(d), grid: true, axis: "top" },
    y: { domain: pts.map((p) => p.label), label: null, tickSize: 0, tickFormat: (d: string) => { const max = narrow ? 24 : 34; return d.length > max ? `${d.slice(0, max - 1)}…` : d; } },
    marks: [
      Plot.ruleX([0], { stroke: "var(--ink-3)" }),
      Plot.ruleX([limit], { stroke: "var(--bad)", strokeDasharray: "4,3" }),
      Plot.text([limit], { x: (d: number) => d, frameAnchor: "bottom", dy: -4, dx: 4, textAnchor: "start", text: () => `limit ${(limit * 100).toFixed(1)}%`, fill: "var(--bad)", fontFamily: "var(--mono)" }),
      Plot.barX(pts.filter((p) => p.key === selected), { y: "label", x1: Math.min(0, ...pts.map((p) => p.low)), x2: maxX, fill: "var(--accent-weak)" }),
      Plot.ruleY(pts, { y: "label", x1: "low", x2: "high", stroke: color, strokeOpacity: 0.7 }),
      Plot.dot(pts.filter((p) => p.status !== "watch"), { y: "label", x: "value", fill: color, r: 3.2 }),
      Plot.dot(pts.filter((p) => p.status === "watch"), { y: "label", x: "value", stroke: "var(--bad)", fill: "var(--bg)", strokeWidth: 1.5, r: 3.4 }),
    ],
  });
}

export const budget: Page = {
  path: "/budget",
  nav: "Budget simulator",
  title: "Most segments can take the full 1.388%; dance videos cannot",
  question: "How much exploration can a segment take before a guardrail breaks?",
  data: ["budget"],
  stripNote: "Budget derived from Comparison A estimates",
  notes: [
    "The simulator assumes a linear effect within the observed range of exploration shares (0.658% to 1.388% of tab-1 impressions): at share s, a guardrail changes by s times the segment's relative effect. Shares above 1.388% were never observed and need a new test.",
    "Guardrail changes are for the whole feed. User segments use their own recommended rate as the base; content segments use the whole feed's rate, because the feed is not split by the type of the random video.",
    "Costs per 1,000 impressions use the segment's random-minus-recommended difference from Comparison A, times the share.",
  ],
  render(root, data) {
    const rows = data.tables.budget;
    const estimates = new Map(data.tables.budget_estimates.map((e) => [key(e), e]));
    const label = labeler(data);
    const facts = data.tables.budget_facts[0];
    const state = { seg: "overall/all", share: SHARE_MAX, limit: PREREG_LIMIT };

    // Controls
    const select = el("select", { id: "seg", class: "control" });
    for (const d of DIMENSIONS) {
      const group = el("optgroup", { label: d.group });
      rows
        .filter((r) => r.dimension === d.key)
        .map((r) => ({ r, l: label(r) }))
        .sort((a, b) => (d.key === "category_segment" ? a.l.localeCompare(b.l) : 0))
        .forEach(({ r, l }) => group.append(el("option", { value: key(r) }, l)));
      select.append(group);
    }
    const slider = el("input", {
      id: "share",
      type: "range",
      min: String(SHARE_MIN * 100),
      max: String(SHARE_MAX * 100),
      step: "0.001",
      value: String(SHARE_MAX * 100),
      "aria-describedby": "share-note",
    });
    const shareOut = el("output", { for: "share", class: "control-value" });
    const limitIn = el("input", { id: "limit", type: "number", min: "0.5", max: "10", step: "0.5", value: "2", class: "control limit-input" });
    const limitTag = el("span", { class: "tag" });
    const reset = el("button", { type: "button", class: "link-button" }, "Reset to 2%");

    const controls = el(
      "div",
      { class: "sim-controls" },
      el("label", { for: "seg", class: "control-label" }, "Segment"),
      select,
      el("div", { class: "control-row" }, el("label", { for: "share", class: "control-label" }, "Exploration share"), shareOut),
      el(
        "div",
        { class: "share-track" },
        slider,
        el("div", { class: "untested", "aria-hidden": "true" }, el("span", {}, "Untested, needs a new test")),
      ),
      el("div", { class: "share-scale", id: "share-note" }, el("span", {}, "0.658%"), el("span", {}, "1.388%")),
      el("div", { class: "control-row" }, el("label", { for: "limit", class: "control-label" }, "Guardrail limit, % worse"), el("span", { class: "limit-wrap" }, limitIn, limitTag)),
      reset,
      el("p", { class: "sim-note" }, "Assumes a linear effect within the observed range."),
    );

    // Outputs
    const badge = el("div", { class: "status" });
    const bindingLine = el("p", { class: "binding-line" });
    const tbody = el("tbody");
    const table = el(
      "div",
      { class: "table-wrap" },
      el(
        "table",
        { class: "sim-table" },
        el(
          "thead",
          {},
          el(
            "tr",
            {},
            el("th", { scope: "col", class: "c-metric" }, "Guardrail"),
            el("th", { scope: "col", class: "num" }, "Change in the feed's rate, 95% interval"),
            el("th", { scope: "col", class: "num" }, "Relative change, 95% interval"),
            el("th", { scope: "col", class: "num" }, "Limit"),
          ),
        ),
        tbody,
      ),
    );
    const costs = el("div", { class: "stats sim-costs" });
    const outputs = el("div", { class: "sim-outputs", "aria-live": "polite" }, badge, bindingLine, table, el("h3", {}, "Cost per 1,000 feed impressions"), costs);

    const chart = el("figure", { class: "overview-chart" });
    const chartNote = el("p", { class: "section-note" });

    root.append(
      el(
        "div",
        { class: "lede" },
        el(
          "p",
          {},
          `${num(facts, "n_no_guardrail_crossed")} of ${num(facts, "n_segments")} segments cross no guardrail up to 1.388%. Dance videos cross the hate limit even at the lowest share in the data. Pick a segment and a share to see what exploration costs and how close each guardrail gets to its limit.`,
        ),
      ),
      el("section", { class: "sim", "aria-label": "Budget simulator" }, controls, outputs),
      el(
        "section",
        { class: "overview", "aria-labelledby": "overview-title" },
        el("h2", { id: "overview-title" }, "Hate at 1.388% against its limit, every segment"),
        chartNote,
        chart,
      ),
    );

    const stat = (value: string, l: string) => el("div", { class: "stat" }, el("span", { class: "stat-value" }, value), el("span", { class: "stat-label" }, l));
    let drawnWidth = 0;
    const drawChart = () => {
      const w = Math.min(chart.clientWidth, 1100);
      if (w <= 0) return;
      drawnWidth = w;
      chart.replaceChildren(overview(rows, label, state.limit, state.seg, w));
    };

    const update = () => {
      const row = rows.find((r) => key(r) === state.seg)!;
      const what = Math.abs(state.limit - PREREG_LIMIT) > 1e-12;
      shareOut.textContent = fmtShare(state.share);
      limitTag.textContent = what ? "what-if" : "pre-registered";
      limitTag.className = what ? "tag tag-whatif" : "tag";
      const st = status(row, state.limit);
      badge.className = `status status-${st}`;
      badge.replaceChildren(el("span", { class: "status-badge" }, STATUS_TEXT[st].badge), el("span", { class: "status-detail" }, STATUS_TEXT[st].detail));
      const b = binding(row, state.limit);
      const gName = (g: Guardrail | null) => (g === "fast_skip" ? "Fast skip" : "Hate");
      bindingLine.textContent = !b.inRange
        ? `No guardrail reaches the ${(state.limit * 100).toFixed(1)}% limit up to 1.388%.`
        : b.belowRange
          ? `${gName(b.guardrail)} is already past the ${(state.limit * 100).toFixed(1)}% limit at 0.658%, the lowest share in the data.`
          : `${gName(b.guardrail)} reaches the ${(state.limit * 100).toFixed(1)}% limit at a share of ${fmtShare(b.share!)}.`;
      tbody.replaceChildren(
        guardrailRow("Hate (dislike button)", guardrailChange(row, "hate", state.share), state.limit),
        guardrailRow("Fast skip (under 3 s)", guardrailChange(row, "fast_skip", state.share), state.limit),
      );
      const c = costsPer1000(estimates.get(state.seg)!, state.share);
      costs.replaceChildren(
        stat(per1000(c.effectiveView), "effective views"),
        stat(per1000(c.newAuthorFollow), "follows of a new creator"),
        stat(per1000(c.newCategoryEffectiveView), "effective views in a new category"),
      );
      chartNote.textContent = `Relative change in the hate rate at a 1.388% share, with its 95% interval, sorted. Red filled: actionable. Red outline: watch list. The dashed line is the ${what ? "what-if " : ""}limit of ${(state.limit * 100).toFixed(1)}%. The selected segment is shaded.`;
      drawChart();
    };

    select.addEventListener("change", () => {
      state.seg = select.value;
      update();
    });
    slider.addEventListener("input", () => {
      state.share = Number(slider.value) / 100;
      update();
    });
    limitIn.addEventListener("input", () => {
      const v = Number(limitIn.value);
      if (Number.isFinite(v) && v > 0) {
        state.limit = v / 100;
        update();
      }
    });
    reset.addEventListener("click", () => {
      limitIn.value = "2";
      state.limit = PREREG_LIMIT;
      update();
    });
    new ResizeObserver(() => {
      if (Math.min(chart.clientWidth, 1100) !== drawnWidth) drawChart();
    }).observe(chart);
    update();
  },
};
