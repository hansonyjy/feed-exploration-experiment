import * as Plot from "@observablehq/plot";
import { num, type Row } from "../data";
import { pct, pp, share, sig } from "../format";
import { card, el } from "../ui";
import type { Data, Page } from "./page";

interface Metric {
  key: string;
  label: string;
  short?: string; // label on phone-width screens
  primary?: boolean;
  seconds?: boolean; // watch time is in milliseconds in the export, not a rate
}

const ENGAGEMENT: Metric[] = [
  { key: "effective_view", label: "Effective view", primary: true },
  { key: "naive_completion", label: "Completed view" },
  { key: "watch_time_ms", label: "Watch time", seconds: true },
  { key: "like_", label: "Like" },
  { key: "comment_", label: "Comment" },
  { key: "forward_", label: "Share" },
  { key: "profile_enter", label: "Profile visit" },
  { key: "new_author_follow", label: "Follow a new creator", short: "New creator follow" },
  { key: "new_category_effective_view", label: "Effective view, new category", short: "New-category view" },
];

const GUARDRAILS: Metric[] = [
  { key: "hate", label: "Hate (dislike button)", short: "Hate" },
  { key: "fast_skip", label: "Fast skip" },
];

type Mode = "absolute" | "relative";

interface Point {
  label: string;
  primary: boolean;
  value: number;
  low: number;
  high: number;
  text: string;
}

function mainRows(data: Data): Map<string, Row> {
  const rows = data.tables.comparison_a.filter(
    (r) => r.analysis === "A_request" && r.variant === "main" && r.weighting === "equal_user",
  );
  return new Map(rows.map((r) => [String(r.metric), r]));
}

function points(metrics: Metric[], rows: Map<string, Row>, mode: Mode, narrow: boolean): Point[] {
  return metrics
    .filter((m) => mode === "relative" || !m.seconds)
    .map((m) => {
      const r = rows.get(m.key)!;
      const base = num(r, "baseline_rec");
      const [est, lo, hi] = [num(r, "estimate"), num(r, "ci_low"), num(r, "ci_high")];
      // On phones the primary row is marked by its shading alone (explained in the caption).
      const label = narrow ? (m.short ?? m.label) : m.primary ? `${m.label} (primary)` : m.label;
      if (mode === "relative") {
        return { label, primary: !!m.primary, value: est / base, low: lo / base, high: hi / base, text: pct(est / base) };
      }
      return { label, primary: !!m.primary, value: est, low: lo, high: hi, text: pp(est, sig(est * 100)) };
    });
}

// Values printed beside each interval, on the side away from zero; the primary metric in bold.
function valueLabels(pts: Point[]) {
  const groups: [boolean, boolean][] = [[true, true], [true, false], [false, true], [false, false]];
  return groups.map(([neg, primary]) =>
    Plot.text(
      pts.filter((p) => p.value < 0 === neg && p.primary === primary),
      {
        y: "label",
        x: neg ? "low" : "high",
        text: "text",
        textAnchor: neg ? "end" : "start",
        dx: neg ? -6 : 6,
        fill: "currentColor",
        fontWeight: primary ? 700 : 400,
      },
    ),
  );
}

function forest(pts: Point[], width: number, narrow: boolean): Element {
  const lo = Math.min(0, ...pts.map((p) => p.low));
  const hi = Math.max(0, ...pts.map((p) => p.high));
  const span = hi - lo || 1;
  // Room for the printed values on the side away from zero.
  const pad = span * (narrow ? 0.5 : 0.32);
  const domain = [lo < 0 ? lo - pad : 0, hi > 0 ? hi + pad : 0];
  return Plot.plot({
    width,
    height: 34 * pts.length + 36,
    marginLeft: narrow ? 116 : 210,
    marginRight: 12,
    style: { fontSize: narrow ? "11px" : "13px" },
    x: { domain, label: null, tickFormat: () => "", ticks: [0], tickSize: 0 },
    y: { domain: pts.map((p) => p.label), label: null, tickSize: 0, tickPadding: 8 },
    marks: [
      Plot.barX(pts.filter((p) => p.primary), {
        y: "label",
        x1: domain[0],
        x2: domain[1],
        fill: "var(--accent-soft)",
        insetTop: 2,
        insetBottom: 2,
      }),
      Plot.ruleX([0], { stroke: "currentColor", strokeOpacity: 0.35 }),
      Plot.ruleY(pts, { y: "label", x1: "low", x2: "high", stroke: "var(--accent)", strokeWidth: 2 }),
      Plot.dot(pts, { y: "label", x: "value", fill: "var(--accent)", r: 4.5 }),
      ...valueLabels(pts),
    ],
  });
}

function comparison(root: HTMLElement, rows: Map<string, Row>): void {
  let mode: Mode = "absolute";
  const buttons = (["absolute", "relative"] as Mode[]).map((m) =>
    el("button", { type: "button", "data-mode": m, "aria-pressed": String(m === mode) }, m === "absolute" ? "Absolute (pp)" : "Relative (%)"),
  );
  const toggle = el("div", { class: "toggle", role: "group", "aria-label": "Show changes as" }, ...buttons);
  const panels = el("div", { class: "panels" });
  const note = el("p", { class: "chart-note" });
  const section = el(
    "section",
    { class: "comparison" },
    el("h2", {}, "What a random slot changes, metric by metric"),
    el(
      "p",
      { class: "muted" },
      "Random slot minus recommended slot in the same feed request, with 95% intervals. pp means percentage points: a rate going from 50% to 45% is −5 pp, or −10% relative.",
    ),
    toggle,
    panels,
    note,
  );
  root.append(section);

  const draw = () => {
    const width = Math.min(panels.clientWidth || 720, 800);
    const narrow = width < 520;
    const unit = mode === "absolute" ? "Change in percentage points" : "Change relative to the recommended rate";
    const primaryNote = narrow ? ". Shaded row: the primary metric." : "";
    panels.replaceChildren(
      el("figure", { class: "chart" }, el("figcaption", {}, el("strong", {}, "Engagement and discovery"), el("span", { class: "axis-title" }, unit + primaryNote)), forest(points(ENGAGEMENT, rows, mode, narrow), width, narrow)),
      el("figure", { class: "chart" }, el("figcaption", {}, el("strong", {}, "Guardrails (higher is worse)"), el("span", { class: "axis-title" }, unit)), forest(points(GUARDRAILS, rows, mode, narrow), width, narrow)),
    );
    const wt = rows.get("watch_time_ms")!;
    note.textContent =
      mode === "absolute"
        ? `Watch time is in seconds, so it is not on the percentage-point scale: ${(num(wt, "estimate") / 1000).toFixed(1).replace("-", "−")} s per impression (${pct(num(wt, "relative"))}).`
        : "Relative change: the difference divided by the recommended slot's rate.";
    for (const b of buttons) b.setAttribute("aria-pressed", String(b.dataset.mode === mode));
  };
  for (const b of buttons) {
    b.addEventListener("click", () => {
      mode = b.dataset.mode as Mode;
      draw();
    });
  }
  requestAnimationFrame(draw);
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
    "Comparison: random vs recommended items in the same feed request, Apr 23 to May 8, 2022, each user weighted equally. Intervals come from resampling users (2,000 times) and are cross-checked with a regression.",
  ],
  render(root, data) {
    const rows = mainRows(data);
    const ev = rows.get("effective_view")!;
    const hate = rows.get("hate")!;
    const c = data.tables.comparison_c.filter((r) => r.variant === "main" && r.metric === "effective_view");
    const term = (t: string) => num(c.find((r) => r.term === t)!, "estimate");
    const targetingShare = term("targeting") / term("total");
    // Dance has no share (it binds below the observed range), so nulls are skipped.
    const topShare = Math.max(...data.tables.budget.map((r) => r.recommended_share).filter((v): v is number => typeof v === "number"));

    root.append(
      el(
        "div",
        { class: "lede" },
        el("p", {}, "KuaiRand is a public dataset of viewing logs from Kuaishou, a large short-video app."),
        el(
          "p",
          {},
          "For a small share of feed requests, the app swapped one recommended video for a random one. Each random slot is therefore a measured exploration slot: a video the feed would not have picked.",
        ),
      ),
      el(
        "section",
        { class: "decision", "aria-labelledby": "decision-title" },
        el("h2", { id: "decision-title" }, "Decision"),
        el(
          "ul",
          {},
          el("li", {}, el("strong", {}, `At least ${share(topShare)} is supported with no guardrail crossed.`), ` ${share(topShare)} is the highest share in the data, not an optimum. Higher shares need a new test.`),
          el("li", {}, el("strong", {}, "Keep dance videos out of the random pool."), " Dance is the only content type where hate clearly rises past its limit."),
          el("li", {}, el("strong", {}, "Next, test 2-3% targeted exploration."), " Most of the cost comes from who sees a random video, not from the videos themselves."),
        ),
      ),
      el(
        "div",
        { class: "cards" },
        card({ value: `${pp(num(ev, "estimate"))} (${pct(num(ev, "relative"))})`, label: "Effective views in a random slot vs a recommended one" }),
        card({ value: `${Math.round(targetingShare * 100)}%`, label: "of that gap is targeting: who sees the video, not the video itself" }),
        card({
          value: pp(num(hate, "estimate"), 3),
          label: `Hate in a random slot: about 1 extra per ${(Math.round(1 / num(hate, "estimate") / 100) * 100).toLocaleString("en-US")} random slots`,
        }),
      ),
    );
    comparison(root, rows);
  },
};
