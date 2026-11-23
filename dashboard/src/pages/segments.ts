import * as Plot from "@observablehq/plot";
import { num, type Row } from "../data";
import { pct, pp, sig } from "../format";
import { chartLabel, el } from "../ui";
import type { Page } from "./page";

// Every number comes from segments.json (segment_points, segment_reference, segment_labels,
// segment_callouts, new_category_note, segments_facts), derived in scripts/build_dashboard_data.py.

const METRICS: { key: string; label: string; guardrail?: boolean }[] = [
  { key: "effective_view", label: "Effective view" },
  { key: "new_category_effective_view", label: "Effective view, new category" },
  { key: "hate", label: "Hate (dislike button)", guardrail: true },
  { key: "fast_skip", label: "Fast skip (under 3 s)", guardrail: true },
];

const PANELS: { group: string; dims: { key: string; title: string; byValue?: boolean }[] }[] = [
  {
    group: "Content: the random video",
    dims: [
      { key: "category_segment", title: "Category", byValue: true },
      { key: "duration_bucket", title: "Video length" },
    ],
  },
  {
    group: "Users",
    dims: [
      { key: "activity_tercile", title: "Activity before the test" },
      { key: "tenure_band", title: "Account age" },
      { key: "follow_band", title: "Accounts followed" },
      { key: "active_group", title: "App's activity group" },
    ],
  },
];

type Mode = "absolute" | "relative";

interface Point {
  key: string;
  label: string;
  value: number;
  low: number;
  high: number;
  marker: string;
  mixed: boolean;
  tip: string;
  order: number;
}

function fmt(x: number, mode: Mode): string {
  return mode === "absolute" ? pp(x, sig(x * 100)) : pct(x);
}

function panel(pts: Point[], domain: [number, number], ref: number, width: number, showAxis: boolean): Element {
  const narrow = width < 600;
  const max = narrow ? 22 : 44;
  const short = (s: string) => chartLabel(s, narrow, max);
  const color = (p: Point) => (p.mixed ? "var(--ink-3)" : "var(--ink)");
  const markX = domain[1];
  return Plot.plot({
    width,
    height: pts.length * 20 + (showAxis ? 30 : 10),
    marginLeft: narrow ? 140 : 280,
    marginRight: 28,
    marginTop: showAxis ? 24 : 4,
    marginBottom: 6,
    style: { fontFamily: "var(--sans)", fontSize: narrow ? "11px" : "12px" },
    x: { domain, label: null, tickFormat: (d: number) => (Math.abs(domain[1] - domain[0]) < 0.02 ? `${(d * 100).toFixed(2)}` : `${Math.round(d * 100)}`), axis: showAxis ? "top" : null },
    y: { domain: pts.map((p) => p.label), axis: null },
    marks: [
      Plot.gridX({ stroke: "var(--rule)", strokeOpacity: 1 }),
      Plot.ruleX([0], { stroke: "var(--ink-3)" }),
      Plot.ruleX([ref], { stroke: "var(--accent)", strokeDasharray: "4,3" }),
      Plot.text(pts, { y: "label", text: (p: Point) => short(p.label), frameAnchor: "left", textAnchor: "end", dx: -8, fill: (p: Point) => (p.mixed ? "var(--ink-3)" : "var(--ink)") }),
      Plot.ruleY(pts, { y: "label", x1: "low", x2: "high", stroke: color, strokeOpacity: 0.55, strokeWidth: 1.5 }),
      Plot.dot(pts, { y: "label", x: "value", fill: color, r: 3.2 }),
      // Contrast with the rest of the dimension: filled = BH and BY finding, outline = BH only.
      Plot.dot(pts.filter((p) => !p.mixed && p.marker === "strong"), { y: "label", x: markX, dx: 18, symbol: "diamond", fill: "var(--accent)", r: 4 }),
      Plot.dot(pts.filter((p) => !p.mixed && p.marker === "bh"), { y: "label", x: markX, dx: 18, symbol: "diamond", stroke: "var(--accent)", fill: "var(--bg)", strokeWidth: 1.3, r: 4 }),
      Plot.tip(pts, Plot.pointerY({ y: "label", x: "value", title: "tip" })),
    ],
  });
}

function callout(value: string, text: string): HTMLElement {
  return el("div", { class: "callout" }, el("span", { class: "callout-value" }, value), el("span", { class: "callout-text" }, text));
}

export const segments: Page = {
  path: "/segments",
  nav: "Segments",
  title: "The cost depends more on what is shown than on who sees it",
  question: "Which content and which users absorb exploration best?",
  data: ["segments"],
  notes: [
    "Segments come from data before the test period only (Apr 8 to 21, 2022). Content segments describe the random video; user segments describe the user.",
    "Each segment's effect is compared with the rest of its group. Benjamini-Hochberg (BH) and the stricter Benjamini-Yekutieli (BY) correct for testing many segments at once. A contrast counts as a finding only if both methods (bootstrap and regression) pass it with the same sign.",
    "Mixed category groups were formed for sample size only. They have no topical meaning and are not interpreted; hover for their categories.",
    "Relative intervals are the absolute interval divided by the segment's recommended rate.",
  ],
  agreement(data) {
    return data.tables.segments_facts[0].effective_view_methods_agree_all === true ? "Bootstrap and regression agree on effective view in every segment" : null;
  },
  render(root, data) {
    const labels = new Map(data.tables.segment_labels.map((r) => [`${r.dimension}/${r.segment}`, r]));
    const ref = new Map(data.tables.segment_reference.map((r) => [String(r.metric), r]));
    const c = data.tables.segment_callouts[0];
    const state: { metric: string; mode: Mode } = { metric: "effective_view", mode: "absolute" };

    const select = el("select", { id: "seg-metric", class: "control" }, ...METRICS.map((m) => el("option", { value: m.key }, m.label)));
    const modeButtons = (["absolute", "relative"] as Mode[]).map((m) =>
      el("button", { type: "button", class: "tab", "data-mode": m, "aria-pressed": String(m === state.mode) }, m === "absolute" ? "Absolute (pp)" : "Relative (%)"),
    );
    const caption = el("p", { class: "section-note" });
    const ncNote = el("p", { class: "nc-note" });
    const charts = el("div", { class: "seg-panels" });

    const p1 = (x: number) => pp(x, 1).replace("+", "");
    const n1 = (x: number) => `${x < 0 ? "−" : ""}${Math.abs(x * 100).toFixed(1)}`;
    root.append(
      el(
        "div",
        { class: "lede" },
        el(
          "p",
          {},
          `Every segment pays a large cost, but the type of video matters most: random ${String(c.worst_label).toLowerCase()} videos cost ${p1(num(c, "worst_estimate"))} of effective views and ${String(c.best_label).toLowerCase()} videos ${p1(num(c, "best_estimate"))}, while user groups differ by a few points.`,
        ),
      ),
      el(
        "section",
        { class: "callouts", "aria-label": "Key differences in effective views" },
        callout(`${p1(num(c, "worst_estimate"))} vs ${p1(num(c, "best_estimate"))}`, `${c.worst_label} videos cost the most, ${String(c.best_label).toLowerCase()} the least.`),
        callout(
          `${n1(num(c, "short_min_cost"))} to ${n1(num(c, "short_max_cost"))} vs ${n1(num(c, "long_min_cost"))} to ${n1(num(c, "long_max_cost"))} pp`,
          "Videos under a minute cost less than longer videos.",
        ),
        callout(
          `${p1(num(c, "most_active_estimate"))} (${pct(num(c, "most_active_relative"))})`,
          `${c.most_active_label} lose the fewest effective views in pp but the most in relative terms, because their recommended rate is lower (${(num(c, "most_active_baseline") * 100).toFixed(1)}% vs ${(num(c, "low_active_baseline") * 100).toFixed(1)}% for ${String(c.low_active_label).toLowerCase()}, who lose ${p1(num(c, "low_active_estimate"))}, ${pct(num(c, "low_active_relative"))}).`,
        ),
      ),
      el(
        "section",
        { class: "seg-main", "aria-labelledby": "seg-title" },
        el("h2", { id: "seg-title" }, "Random minus recommended, by segment"),
        el(
          "div",
          { class: "seg-controls" },
          el("label", { for: "seg-metric", class: "control-label" }, "Metric"),
          select,
          el("div", { class: "tabs", role: "group", "aria-label": "Show changes as" }, ...modeButtons),
        ),
        caption,
        ncNote,
        charts,
        el(
          "p",
          { class: "figure-note" },
          "At this sample size nearly every contrast passes a significance test, so how large an effect is matters more than whether it is marked.",
        ),
      ),
    );

    let drawn = 0;
    const draw = () => {
      const w = Math.min(charts.clientWidth, 1000);
      if (w <= 0) return;
      drawn = w;
      const mode = state.mode;
      const rows = data.tables.segment_points.filter((r) => r.metric === state.metric);
      const pick = (r: Row) => (mode === "absolute" ? [num(r, "estimate"), num(r, "ci_low"), num(r, "ci_high")] : [num(r, "relative"), num(r, "relative_ci_low"), num(r, "relative_ci_high")]);
      const all = rows.map(pick).flat();
      const refRow = ref.get(state.metric)!;
      const refVal = mode === "absolute" ? num(refRow, "estimate") : num(refRow, "relative");
      // Zero is on the axis only when the data comes near it; effective-view costs sit far from zero.
      let lo = Math.min(refVal, ...all);
      let hi = Math.max(refVal, ...all);
      if (lo > 0 && lo < (hi - lo) * 0.5) lo = 0;
      if (hi < 0 && -hi < (hi - lo) * 0.5) hi = 0;
      const pad = (hi - lo) * 0.04;
      const domain: [number, number] = [lo - pad, hi + pad];
      const metricLabel = METRICS.find((m) => m.key === state.metric)!.label;
      caption.textContent = `${metricLabel}, random minus recommended, ${mode === "absolute" ? "in percentage points" : "relative to the segment's recommended rate (%)"}, with 95% intervals. Dashed blue line: the whole feed (${fmt(refVal, mode)}). Diamond: the segment differs from the rest of its group, filled if it passes both BH and the stricter BY, outline if BH only. Grey: mixed category groups, not interpreted.`;
      const n = data.tables.new_category_note[0];
      const v = (col: string) => {
        const x = num(n, col);
        const agree = n[col.replace("_estimate", "_agree")] === true;
        return `${pp(x, sig(x * 100))}${agree ? "" : ", not a finding"}`;
      };
      ncNote.hidden = state.metric !== "new_category_effective_view";
      ncNote.replaceChildren(el("strong", {}, "New categories: "), `${n.mid_label} and ${String(n.most_label).toLowerCase()} get about as many new-category effective views from random slots as from recommended ones (${v("mid_estimate")} and ${v("most_estimate")}). ${n.low_label} get far fewer (${v("low_estimate")}; ${n.group_label}: ${v("group_estimate")}). Part of this is mechanical: users with little history have more categories that count as new.`);
      const blocks: HTMLElement[] = [];
      PANELS.forEach((g) => {
        blocks.push(el("h3", { class: "seg-group" }, g.group));
        g.dims.forEach((d, di) => {
          const pts: Point[] = rows
            .filter((r) => r.dimension === d.key)
            .map((r) => {
              const lab = labels.get(`${r.dimension}/${r.segment}`)!;
              const [value, low, high] = pick(r);
              const mixed = lab.mixed === true;
              const tip = `${lab.label}${mixed ? `\nCategories: ${lab.members}` : ""}\n${fmt(value, mode)} (${fmt(low, mode)} to ${fmt(high, mode)})`;
              return { key: `${r.dimension}/${r.segment}`, label: String(lab.label), value, low, high, marker: String(r.marker), mixed, tip, order: Number(lab.order) };
            })
            .sort((a, b) => (d.byValue ? Number(a.mixed) - Number(b.mixed) || a.value - b.value : a.order - b.order));
          blocks.push(el("figure", { class: "seg-panel" }, el("figcaption", {}, d.title), panel(pts, domain, refVal, w, di === 0)));
        });
      });
      charts.replaceChildren(...blocks);
      for (const b of modeButtons) b.setAttribute("aria-pressed", String(b.dataset.mode === mode));
    };

    select.addEventListener("change", () => {
      state.metric = select.value;
      draw();
    });
    for (const b of modeButtons) {
      b.addEventListener("click", () => {
        state.mode = b.dataset.mode as Mode;
        draw();
      });
    }
    new ResizeObserver(() => {
      if (Math.min(charts.clientWidth, 1000) !== drawn) draw();
    }).observe(charts);
  },
};
