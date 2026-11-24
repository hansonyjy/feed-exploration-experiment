import * as Plot from "@observablehq/plot";
import { num, type Row } from "../data";
import { pct, pp, share, sig } from "../format";
import { el, repoLink } from "../ui";
import type { Data, Page } from "./page";

// Every number on this page comes from exports/dashboard/headline.json (scorecard, waterfall,
// headline_facts are derived in scripts/build_dashboard_data.py); the browser only formats.

interface Metric {
  key: string;
  label: string;
  primary?: boolean;
  seconds?: boolean; // watch time is in milliseconds, not a rate
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
// One relative axis for every row, so effect sizes and interval widths compare at a glance.
const AXIS = { min: -1, max: 1.5, ticks: [-1, -0.5, 0, 0.5, 1, 1.5], width: 290, pad: 18 };
const ax = (v: number) => AXIS.pad + ((v - AXIS.min) / (AXIS.max - AXIS.min)) * (AXIS.width - 2 * AXIS.pad);

function one(data: Data, table: string): Row {
  return data.tables[table][0];
}

// Rates with the precision the findings tables use: 54.8%, 2.44%, 0.354%.
function rate(x: number): string {
  const v = x * 100;
  const a = Math.abs(v);
  return `${v.toFixed(a >= 10 ? 1 : a >= 1 ? 2 : 3)}%`;
}

function seconds(ms: number, signed = false): string {
  const s = Math.abs(ms / 1000).toFixed(1);
  return signed ? `${ms < 0 ? "−" : "+"}${s} s` : `${s} s`;
}

function bare(x: number, digits: number): string {
  return `${x < 0 ? "−" : ""}${Math.abs(x).toFixed(digits)}`;
}

function svg(w: number, h: number, cls: string[]): SVGSVGElement {
  const s = document.createElementNS(SVG, "svg");
  s.setAttribute("viewBox", `0 0 ${w} ${h}`);
  s.setAttribute("width", String(w));
  s.setAttribute("height", String(h));
  s.setAttribute("aria-hidden", "true");
  s.classList.add(...cls);
  return s;
}

function add(parent: SVGElement, tag: string, attrs: Record<string, string | number>, text?: string): void {
  const n = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v));
  if (text) n.textContent = text;
  parent.append(n);
}

function axisHeader(): SVGSVGElement {
  const s = svg(AXIS.width, 18, ["ci-head"]);
  for (const t of AXIS.ticks) {
    add(s, "text", { x: ax(t), y: 12, "text-anchor": "middle" }, t === 0 ? "0" : pct(t));
  }
  return s;
}

function ciBar(rel: number, lo: number, hi: number, bad: boolean): SVGSVGElement {
  const h = 18;
  const s = svg(AXIS.width, h, ["ci", bad ? "ci-bad" : "ci-neutral"]);
  for (const t of AXIS.ticks) add(s, "line", { x1: ax(t), x2: ax(t), y1: 0, y2: h, class: t === 0 ? "ci-zero" : "ci-grid" });
  add(s, "line", { x1: ax(lo), x2: ax(hi), y1: h / 2, y2: h / 2, class: "ci-range" });
  add(s, "circle", { cx: ax(rel), cy: h / 2, r: 3.5, class: "ci-est" });
  return s;
}

function scorecard(data: Data): HTMLElement {
  const rows = new Map(data.tables.scorecard.map((r) => [String(r.metric), r]));
  const head = el(
    "thead",
    {},
    el(
      "tr",
      {},
      el("th", { scope: "col", class: "c-metric" }, "Metric"),
      el("th", { scope: "col", class: "num" }, "Recommended"),
      el("th", { scope: "col", class: "num" }, "Random"),
      el("th", { scope: "col", class: "num" }, "Δ"),
      el("th", { scope: "col", class: "num" }, "Δ %"),
      el("th", { scope: "col", class: "c-ci" }, el("span", { class: "sr-only" }, "95% interval of Δ %"), axisHeader()),
    ),
  );
  const body = el("tbody");
  for (const g of GROUPS) {
    body.append(
      el("tr", { class: "group" }, el("th", { scope: "rowgroup", colspan: "6" }, g.name, ...(g.note ? [el("span", { class: "group-note" }, ` · ${g.note}`)] : []))),
    );
    for (const m of g.metrics) {
      const r = rows.get(m.key)!;
      const [rec, rnd, est, lo, hi, rel] = ["recommended_rate", "random_rate", "estimate", "ci_low", "ci_high", "relative"].map((c) => num(r, c));
      const bad = !!m.guardrail && est > 0;
      const d = m.seconds ? 1 : sig(est * 100);
      const range = m.seconds ? `${bare(lo / 1000, 1)} to ${bare(hi / 1000, 1)} s` : `${bare(lo * 100, d)} to ${bare(hi * 100, d)} pp`;
      const name = el("th", { scope: "row", class: "c-metric" }, m.label);
      if (m.primary) name.append(el("span", { class: "tag" }, "primary"));
      body.append(
        el(
          "tr",
          { class: [m.primary ? "primary" : "", bad ? "bad" : ""].join(" ").trim() },
          name,
          el("td", { class: "num" }, m.seconds ? seconds(rec) : rate(rec)),
          el("td", { class: "num" }, m.seconds ? seconds(rnd) : rate(rnd)),
          el("td", { class: "num delta" }, m.seconds ? seconds(est, true) : pp(est, d)),
          el("td", { class: "num delta" }, pct(rel)),
          el("td", { class: "c-ci" }, ciBar(rel, num(r, "relative_ci_low"), num(r, "relative_ci_high"), bad), el("span", { class: "ci-text" }, range)),
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
      "Same feed request, each user weighted equally. Δ is random minus recommended; pp means percentage points (50% to 45% is −5 pp, or −10%). The bars share one axis in Δ %: a dot and its 95% interval. Red marks a guardrail getting worse.",
    ),
    el("div", { class: "table-wrap" }, el("table", {}, head, body)),
  );
}

function millions(n: number): string {
  return `${(n / 1e6).toFixed(1)}M`;
}

// "How this was built": scale numbers (build_facts, from committed files), pipeline, methods.
function howBuilt(f: Row): HTMLElement {
  const stat = (value: string, label: string) =>
    el("div", { class: "stat" }, el("span", { class: "stat-value" }, value), el("span", { class: "stat-label" }, label));
  const steps: [string, string][] = [
    ["Raw logs", `${millions(num(f, "raw_log_rows"))} rows`],
    ["BigQuery", "date-partitioned"],
    ["dbt staging", `${num(f, "n_models_staging")} models`],
    ["Intermediate", `${num(f, "n_models_intermediate")} models`],
    ["Marts", `${num(f, "n_models_marts")} models`],
    ["Python", "bootstrap, regression"],
    ["exports/", "CSV, JSON"],
    ["This site", "static"],
  ];
  return el(
    "section",
    { class: "built", "aria-labelledby": "built-title" },
    el("h2", { id: "built-title" }, "How this was built"),
    el(
      "div",
      { class: "stats" },
      stat(millions(num(f, "raw_log_rows")), "raw log rows"),
      stat(num(f, "n_users_dataset").toLocaleString("en-US"), "users in dataset"),
      stat(millions(num(f, "n_videos")), "videos"),
      stat(`${Math.round(num(f, "bytes_billed_total") / 1e9)} GB`, "scanned in BigQuery"),
      stat(String(num(f, "n_models")), "dbt models"),
      stat(String(num(f, "n_tests")), "tests"),
    ),
    el(
      "ol",
      { class: "pipeline", "aria-label": "Pipeline" },
      ...steps.map(([name, sub]) => el("li", {}, el("span", { class: "step-name" }, name), el("span", { class: "step-sub" }, sub))),
    ),
    el(
      "ul",
      { class: "methods" },
      el("li", {}, el("strong", {}, "Within-request comparison."), " Each random video is compared with the recommended videos in the same feed request."),
      el("li", {}, el("strong", {}, "User-clustered bootstrap."), " 2,000 resamples of users, cross-checked with a fixed-effects regression."),
      el("li", {}, el("strong", {}, "Pre-registered."), " Metrics, tests and parameters were fixed before any outcome was read."),
      el("li", {}, el("strong", {}, "Corrected segment tests."), " Benjamini-Hochberg, with Benjamini-Yekutieli as a stricter check."),
      el("li", {}, el("strong", {}, "Duration-adjusted effective view."), " A view counts if it lasts at least as long as the median view of videos of similar length."),
    ),
  );
}

interface Step {
  label: string;
  y1: number;
  y2: number;
  kind: "level" | "content" | "targeting";
  value: string;
}

function waterfall(w: Row, width: number): Element {
  const [rec, content, targeting, random] = ["recommended_rate", "content_gap", "targeting_gap", "random_rate"].map((c) => num(w, c));
  const steps: Step[] = [
    { label: "Recommended", y1: 0, y2: rec, kind: "level", value: rate(rec) },
    { label: "Content gap", y1: rec - content, y2: rec, kind: "content", value: pp(-content) },
    { label: "Targeting gap", y1: random, y2: rec - content, kind: "targeting", value: pp(-targeting) },
    { label: "Random", y1: 0, y2: random, kind: "level", value: rate(random) },
  ];
  const narrow = width < 560;
  const gapShare = `${Math.round(num(w, "targeting_share") * 100)}%`;
  const mid = (random + rec - content) / 2;
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
            Plot.text([{ x: "Targeting gap", y: mid }], {
              x: "x",
              y: "y",
              text: () => `${gapShare}\nof the\ngap`,
              fill: "var(--surface)",
              fontFamily: "var(--sans)",
              fontWeight: 600,
              fontSize: 12,
            }),
          ]
        : [
            Plot.text([{ x: "Targeting gap", y: mid }], {
              x: "x",
              y: "y",
              dx: 46,
              textAnchor: "start",
              lineWidth: 12,
              text: () => `${gapShare} of the gap. The same videos do well when recommended to the right people.`,
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
  title: "Exploration’s real cost is bad targeting, not bad videos",
  question: "What does a random slot cost compared with a recommended one, and what should the feed do about it?",
  data: ["headline"],
  notes: [
    "Effective view: watch time at least as long as the median view of videos of similar length. It is the primary metric because plain completion favors short videos.",
    "Guardrail: a metric that may get worse by at most 2% relative, at the level of the whole feed. The two guardrails are hate (the user presses the dislike button) and fast skip (watched for less than 3 seconds).",
    "Intervals come from resampling users (2,000 times) and are cross-checked with a regression. A relative interval is the absolute interval divided by the recommended rate.",
  ],
  dataNotes(data) {
    const f = one(data, "build_facts");
    return [
      `BigQuery bytes: total billed by query jobs in this project through ${f.bytes_snapshot_date}, from a snapshot written by scripts/export_build_stats.py.`,
    ];
  },
  agreement(data) {
    const f = one(data, "headline_facts");
    return f.all_methods_agree === true ? `Bootstrap and regression agree on all ${f.n_metrics} metrics` : null;
  },
  render(root, data) {
    const w = one(data, "waterfall");
    const topShare = share(num(one(data, "headline_facts"), "top_share"));
    const decision1 = [
      el("strong", {}, `At least ${topShare} of the feed can go to exploration with no guardrail crossed.`),
      " It is the highest share in the data, not an optimum. Higher shares need a new test.",
    ];

    const chart = el("figure", { class: "hero-chart" });
    root.append(
      el("p", { class: "memo-link" }, repoLink("docs/memo.md", "Read the decision memo"), " · ", repoLink("docs/memo.pdf", "PDF, one page")),
      el(
        "div",
        { class: "lede" },
        el(
          "p",
          {},
          "KuaiRand is a public dataset of viewing logs from Kuaishou, a large short-video app. For a small share of feed requests, the app swapped one recommended video for a random one, so each random slot is a measured exploration slot.",
        ),
      ),
      el(
        "section",
        { class: "hero" },
        el(
          "div",
          { class: "hero-main" },
          el("h2", {}, "Effective views: where the random slot loses them"),
          el("p", { class: "subtitle" }, `Same-day sample, ${num(w, "n_users").toLocaleString("en-US")} users`),
          chart,
          el("p", { class: "figure-note" }, `The scorecard compares within the same feed request, so its gap is ${pp(num(w, "a_gap")).replace("+", "")}.`),
        ),
        el(
          "aside",
          { class: "decision", "aria-labelledby": "decision-title" },
          el("h2", { id: "decision-title" }, "Decision"),
          el(
            "ol",
            {},
            el("li", {}, ...decision1),
            el("li", {}, el("strong", {}, "Keep dance videos out of the random pool."), " They are the only content where hate clearly passes its limit."),
            el("li", {}, el("strong", {}, "Next, test 2-3% targeted exploration."), " Most of the cost is who sees a random video, not the video."),
          ),
        ),
      ),
      scorecard(data),
      howBuilt(one(data, "build_facts")),
    );
    // Redraw when the column width changes (first layout, rotation, window resize).
    let drawn = 0;
    new ResizeObserver(() => {
      const width = Math.min(chart.clientWidth, 760);
      if (width > 0 && width !== drawn) {
        drawn = width;
        chart.replaceChildren(waterfall(w, width));
      }
    }).observe(chart);
  },
};
