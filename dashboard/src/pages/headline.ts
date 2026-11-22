import * as Plot from "@observablehq/plot";
import { num, type Row } from "../data";
import { pct, pp, share, sig } from "../format";
import { el } from "../ui";
import type { Data, Page } from "./page";

interface Metric {
  key: string;
  label: string;
  primary?: boolean;
  seconds?: boolean; // watch time is in milliseconds in the export, not a rate
  guardrail?: boolean;
}

const GROUPS: { name: string; note?: string; metrics: Metric[] }[] = [
  {
    name: "Engagement",
    metrics: [
      { key: "effective_view", label: "Effective view", primary: true },
      { key: "naive_completion", label: "Completed view" },
      { key: "watch_time_ms", label: "Watch time", seconds: true },
      { key: "like_", label: "Like" },
      { key: "comment_", label: "Comment" },
      { key: "forward_", label: "Share" },
      { key: "profile_enter", label: "Profile visit" },
    ],
  },
  {
    name: "Discovery",
    metrics: [
      { key: "new_author_follow", label: "Follow a new creator" },
      { key: "new_category_effective_view", label: "Effective view, new category" },
    ],
  },
  {
    name: "Guardrails",
    note: "lower is better",
    metrics: [
      { key: "hate", label: "Hate (dislike button)", guardrail: true },
      { key: "fast_skip", label: "Fast skip (under 3 s)", guardrail: true },
    ],
  },
];

const SVG = "http://www.w3.org/2000/svg";

function mainRows(data: Data): Map<string, Row> {
  const rows = data.tables.comparison_a.filter(
    (r) => r.analysis === "A_request" && r.variant === "main" && r.weighting === "equal_user",
  );
  return new Map(rows.map((r) => [String(r.metric), r]));
}

// Rates with the precision the findings tables use: 54.8%, 2.44%, 0.354%.
function rate(x: number): string {
  const v = x * 100;
  const a = Math.abs(v);
  return `${v.toFixed(a >= 10 ? 1 : a >= 1 ? 2 : 3)}%`;
}

function seconds(ms: number, signed = false): string {
  const s = Math.abs(ms / 1000).toFixed(1);
  if (!signed) return `${s} s`;
  return `${ms < 0 ? "−" : "+"}${s} s`;
}

function bare(x: number, digits: number): string {
  return `${x < 0 ? "−" : ""}${Math.abs(x).toFixed(digits)}`;
}

// Interval on the row's own symmetric scale (zero in the middle), so small metrics stay readable.
function ciBar(est: number, lo: number, hi: number, bad: boolean): SVGSVGElement {
  const w = 160;
  const h = 18;
  const m = Math.max(Math.abs(lo), Math.abs(hi)) * 1.15 || 1;
  const x = (v: number) => w / 2 + (v / m) * (w / 2 - 3);
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.setAttribute("width", String(w));
  svg.setAttribute("height", String(h));
  svg.setAttribute("aria-hidden", "true");
  svg.classList.add("ci", bad ? "ci-bad" : "ci-neutral");
  const add = (tag: string, attrs: Record<string, string | number>) => {
    const n = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v));
    svg.append(n);
  };
  add("line", { x1: 0, x2: w, y1: h / 2, y2: h / 2, class: "ci-axis" });
  add("line", { x1: w / 2, x2: w / 2, y1: 2, y2: h - 2, class: "ci-zero" });
  add("rect", { x: x(lo), y: h / 2 - 4, width: Math.max(2, x(hi) - x(lo)), height: 8, class: "ci-range" });
  add("line", { x1: x(est), x2: x(est), y1: 2, y2: h - 2, class: "ci-est" });
  return svg;
}

function scorecard(rows: Map<string, Row>): HTMLElement {
  const head = el(
    "thead",
    {},
    el(
      "tr",
      {},
      el("th", { scope: "col", class: "c-metric" }, "Metric"),
      el("th", { scope: "col", class: "num" }, "Δ"),
      el("th", { scope: "col", class: "num" }, "Δ %"),
      el("th", { scope: "col", class: "c-ci" }, "95% interval of Δ"),
      el("th", { scope: "col", class: "num" }, "Recommended"),
      el("th", { scope: "col", class: "num" }, "Random"),
    ),
  );
  const body = el("tbody");
  for (const g of GROUPS) {
    body.append(
      el("tr", { class: "group" }, el("th", { scope: "rowgroup", colspan: "6" }, g.name, ...(g.note ? [el("span", { class: "group-note" }, ` · ${g.note}`)] : []))),
    );
    for (const m of g.metrics) {
      const r = rows.get(m.key)!;
      const [base, est, lo, hi, rel] = ["baseline_rec", "estimate", "ci_low", "ci_high", "relative"].map((c) => num(r, c));
      const bad = !!m.guardrail && est > 0;
      const d = m.seconds ? 1 : sig(est * 100);
      const delta = m.seconds ? seconds(est, true) : pp(est, d);
      const range = m.seconds
        ? `${bare(lo / 1000, 1)} to ${bare(hi / 1000, 1)}`
        : `${bare(lo * 100, d)} to ${bare(hi * 100, d)}`;
      const name = el("th", { scope: "row", class: "c-metric" }, m.label);
      if (m.primary) name.append(el("span", { class: "tag" }, "primary"));
      body.append(
        el(
          "tr",
          { class: [m.primary ? "primary" : "", bad ? "bad" : ""].join(" ").trim() },
          name,
          el("td", { class: "num delta" }, delta),
          el("td", { class: "num delta" }, pct(rel)),
          el("td", { class: "c-ci" }, ciBar(est, lo, hi, bad), el("span", { class: "ci-text" }, range)),
          el("td", { class: "num" }, m.seconds ? seconds(base) : rate(base)),
          el("td", { class: "num" }, m.seconds ? seconds(base + est) : rate(base + est)),
        ),
      );
    }
  }
  return el(
    "section",
    { class: "scorecard", "aria-labelledby": "scorecard-title" },
    el("h2", { id: "scorecard-title" }, "Scorecard: random slot vs recommended slot"),
    el(
      "p",
      { class: "section-note" },
      "Same feed request, each user weighted equally. Δ is random minus recommended; pp means percentage points (50% to 45% is −5 pp, or −10%). Each interval bar has its own scale with zero in the middle. Red marks a guardrail getting worse.",
    ),
    el("div", { class: "table-wrap" }, el("table", {}, head, body)),
  );
}

interface Step {
  label: string;
  y1: number;
  y2: number;
  kind: "level" | "content" | "targeting";
  value: string;
}

function waterfall(data: Data, width: number): Element {
  const c = data.tables.comparison_c.filter((r) => r.variant === "main" && r.metric === "effective_view");
  const term = (t: string) => c.find((r) => r.term === t)!;
  const rec = num(term("total"), "baseline_rec_all");
  const content = num(term("content"), "estimate");
  const targeting = num(term("targeting"), "estimate");
  const random = rec - content - targeting;
  const steps: Step[] = [
    { label: "Recommended", y1: 0, y2: rec, kind: "level", value: rate(rec) },
    { label: "Content gap", y1: rec - content, y2: rec, kind: "content", value: pp(-content) },
    { label: "Targeting gap", y1: random, y2: rec - content, kind: "targeting", value: pp(-targeting) },
    { label: "Random", y1: 0, y2: random, kind: "level", value: rate(random) },
  ];
  const narrow = width < 560;
  const gapShare = Math.round((targeting / (content + targeting)) * 100);
  const fill = (s: Step) => (s.kind === "targeting" ? "var(--accent)" : s.kind === "content" ? "var(--ink-3)" : "var(--ink-2)");
  return Plot.plot({
    width,
    height: narrow ? 300 : 340,
    marginTop: 28,
    marginLeft: 44,
    marginRight: narrow ? 8 : 150,
    marginBottom: 32,
    style: { fontFamily: "var(--mono)", fontSize: "12px" },
    x: { domain: steps.map((s) => s.label), label: null, tickSize: 0, padding: 0.28 },
    y: { domain: [0, 0.6], label: "Effective view rate", tickFormat: (d: number) => `${Math.round(d * 100)}%`, ticks: 6, grid: true },
    marks: [
      Plot.ruleY([0], { stroke: "var(--rule-strong)" }),
      // Dashed connectors carry each level to the next bar.
      Plot.link(
        [
          { x1: "Recommended", x2: "Content gap", y: rec },
          { x1: "Content gap", x2: "Targeting gap", y: rec - content },
          { x1: "Targeting gap", x2: "Random", y: random },
        ],
        { x1: "x1", x2: "x2", y1: "y", y2: "y", stroke: "var(--ink-3)", strokeDasharray: "3,3" },
      ),
      Plot.barY(steps, { x: "label", y1: "y1", y2: "y2", fill }),
      Plot.text(steps, { x: "label", y: "y2", text: "value", dy: -9, fill: "var(--ink)", fontWeight: 500 }),
      ...(narrow
        ? [
            Plot.text([{ x: "Targeting gap", y: (random + rec - content) / 2 }], {
              x: "x",
              y: "y",
              text: () => `${gapShare}%\nof the\ngap`,
              fill: "var(--surface)",
              fontFamily: "var(--sans)",
              fontWeight: 600,
              fontSize: 12,
            }),
          ]
        : [
            Plot.text([{ x: "Targeting gap", y: (random + rec - content) / 2 }], {
              x: "x",
              y: "y",
              dx: 46,
              textAnchor: "start",
              lineWidth: 12,
              text: () => `${gapShare}% of the gap. The same videos do well when recommended to the right people.`,
              fill: "var(--accent-ink)",
              fontFamily: "var(--sans)",
              fontSize: 12.5,
            }),
            Plot.text([{ x: "Content gap", y: rec - content }], {
              x: "x",
              y: "y",
              dy: 26,
              lineWidth: 9,
              text: () => "The videos themselves",
              fill: "var(--ink-2)",
              fontFamily: "var(--sans)",
              fontSize: 12,
            }),
          ]),
    ],
  });
}

export const headline: Page = {
  path: "/",
  nav: "Headline result",
  title: "At least 1.388% of the feed can go to exploration with no guardrail crossed",
  question: "What does a random slot cost compared with a recommended one, and what should the feed do about it?",
  data: ["headline", "decomposition", "budget"],
  notes: [
    "Effective view: watch time at least as long as the median view of videos of similar length. It is the primary metric because plain completion favors short videos.",
    "Guardrail: a metric that may get worse by at most 2% relative, at the level of the whole feed. The two guardrails are hate (the user presses the dislike button) and fast skip (watched for less than 3 seconds).",
    "Intervals come from resampling users (2,000 times) and are cross-checked with a regression.",
  ],
  agreement(data) {
    const rows = [...mainRows(data).values()];
    const all = rows.every((r) => r.bootstrap_and_regression_agree === true);
    return all ? `Bootstrap and regression agree on all ${rows.length} metrics` : null;
  },
  render(root, data) {
    const rows = mainRows(data);
    const c = data.tables.comparison_c.find((r) => r.variant === "main" && r.metric === "effective_view" && r.term === "total")!;
    // Dance has no share (it binds below the observed range), so nulls are skipped.
    const topShare = Math.max(...data.tables.budget.map((r) => r.recommended_share).filter((v): v is number => typeof v === "number"));
    const aGap = -num(rows.get("effective_view")!, "estimate");

    const chart = el("figure", { class: "hero-chart" });
    const hero = el(
      "section",
      { class: "hero" },
      el(
        "div",
        { class: "hero-main" },
        el("h2", {}, "Effective views: where the random slot loses them"),
        chart,
        el(
          "p",
          { class: "figure-note" },
          `Measured on the ${num(c, "n_users").toLocaleString("en-US")} users who saw a recommended pool video on the same day as a random one. On all users, comparing within the same feed request, the gap is ${pp(aGap).replace("+", "")}, as in the scorecard; the difference comes from how days are weighted.`,
        ),
      ),
      el(
        "aside",
        { class: "decision", "aria-labelledby": "decision-title" },
        el("h2", { id: "decision-title" }, "Decision"),
        el(
          "ol",
          {},
          el("li", {}, el("strong", {}, `At least ${share(topShare)} is supported with no guardrail crossed.`), " It is the highest share in the data, not an optimum. Higher shares need a new test."),
          el("li", {}, el("strong", {}, "Keep dance videos out of the random pool."), " They are the only content where hate clearly passes its limit."),
          el("li", {}, el("strong", {}, "Next, test 2-3% targeted exploration."), " Most of the cost is who sees a random video, not the video."),
        ),
      ),
    );
    root.append(
      el(
        "div",
        { class: "lede" },
        el(
          "p",
          {},
          "KuaiRand is a public dataset of viewing logs from Kuaishou, a large short-video app. For a small share of feed requests, the app swapped one recommended video for a random one, so each random slot is a measured exploration slot.",
        ),
      ),
      hero,
      scorecard(rows),
    );
    // Redraw when the column width changes (first layout, rotation, window resize).
    let drawn = 0;
    new ResizeObserver(() => {
      const w = Math.min(chart.clientWidth, 760);
      if (w > 0 && w !== drawn) {
        drawn = w;
        chart.replaceChildren(waterfall(data, w));
      }
    }).observe(chart);
  },
};
