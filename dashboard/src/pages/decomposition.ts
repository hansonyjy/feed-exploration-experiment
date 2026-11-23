import * as Plot from "@observablehq/plot";
import { num, type Row } from "../data";
import { pct, pp, sig } from "../format";
import { el } from "../ui";
import type { Data, Page } from "./page";

// Every number comes from decomposition.json (dumbbell, decomposition_table, pool_length,
// bridge_effective_view, hate_facts, decomposition_facts), derived in scripts/build_dashboard_data.py.

interface Metric {
  key: string;
  label: string;
  primary?: boolean;
  seconds?: boolean;
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
    note: "higher is worse",
    metrics: [
      { key: "hate", label: "Hate (dislike button)", guardrail: true },
      { key: "fast_skip", label: "Fast skip (under 3 s)", guardrail: true },
    ],
  },
];

const LABEL = new Map(GROUPS.flatMap((g) => g.metrics.map((m) => [m.key, m.label] as [string, string])));

// Dumbbell panels: rates on comparable scales share an axis.
const PANELS: { title: string; metrics: string[] }[] = [
  { title: "Viewing", metrics: ["effective_view", "naive_completion", "fast_skip"] },
  { title: "Actions", metrics: ["like_", "profile_enter", "comment_", "new_author_follow"] },
];

function rate(x: number): string {
  const v = x * 100;
  const a = Math.abs(v);
  return `${v.toFixed(a >= 10 ? 1 : a >= 1 ? 2 : 3)}%`;
}

function value(x: number, seconds: boolean, signed = true): string {
  if (seconds) return `${signed ? (x < 0 ? "−" : "+") : ""}${Math.abs(x / 1000).toFixed(1)} s`;
  return signed ? pp(x, sig(x * 100)) : rate(x);
}

function range(lo: number, hi: number, seconds: boolean, digits: number): string {
  const f = (x: number) => (seconds ? `${x < 0 ? "−" : ""}${Math.abs(x / 1000).toFixed(1)}` : `${x < 0 ? "−" : ""}${Math.abs(x * 100).toFixed(digits)}`);
  return `${f(lo)} to ${f(hi)}${seconds ? " s" : " pp"}`;
}

interface Bell {
  label: string;
  rec: number;
  rnd: number;
  gap: string;
  bad: boolean;
}

function dumbbell(rows: Row[], keys: string[], width: number): Element {
  const by = new Map(rows.map((r) => [String(r.metric), r]));
  const bells: Bell[] = keys.map((k) => {
    const r = by.get(k)!;
    const est = num(r, "estimate");
    return { label: LABEL.get(k)!, rec: num(r, "recommended_rate"), rnd: num(r, "random_rate"), gap: pp(est, sig(est * 100)), bad: k === "fast_skip" && est > 0 };
  });
  const narrow = width < 560;
  const max = Math.max(...bells.flatMap((b) => [b.rec, b.rnd])) * 1.12;
  const small = (b: Bell) => Math.abs(b.rec - b.rnd) < max * 0.18;
  return Plot.plot({
    width,
    height: bells.length * 40 + 36,
    marginLeft: narrow ? 110 : 160,
    marginRight: 16,
    marginTop: 26,
    style: { fontFamily: "var(--sans)", fontSize: narrow ? "11px" : "12px" },
    x: { domain: [0, max], label: null, tickFormat: (d: number) => `${Number((d * 100).toFixed(2))}%`, grid: true, axis: "top", ticks: narrow ? 4 : 6 },
    y: { domain: bells.map((b) => b.label), label: null, tickSize: 0, tickPadding: 8 },
    marks: [
      Plot.ruleX([0], { stroke: "var(--rule-strong)" }),
      Plot.link(bells, { y1: "label", y2: "label", x1: "rec", x2: "rnd", stroke: (b: Bell) => (b.bad ? "var(--bad)" : "var(--ink-3)"), strokeWidth: 2 }),
      Plot.dot(bells, { y: "label", x: "rec", fill: "var(--ink)", r: 5 }),
      Plot.dot(bells, { y: "label", x: "rnd", fill: "var(--bg)", stroke: "var(--accent)", strokeWidth: 2, r: 5 }),
      // Gap label above the bar, or to the right of the dots when the bar is too short to hold it.
      Plot.text(bells.filter((b) => !small(b)), { y: "label", x: (b: Bell) => (b.rec + b.rnd) / 2, text: "gap", dy: -11, fill: (b: Bell) => (b.bad ? "var(--bad)" : "var(--ink-2)"), fontFamily: "var(--mono)", fontSize: 11 }),
      Plot.text(bells.filter(small), { y: "label", x: (b: Bell) => Math.max(b.rec, b.rnd), text: "gap", dx: 10, textAnchor: "start", fill: (b: Bell) => (b.bad ? "var(--bad)" : "var(--ink-2)"), fontFamily: "var(--mono)", fontSize: 11 }),
    ],
  });
}

function cell(v: number, lo: number, hi: number, seconds: boolean, significant: boolean): HTMLElement {
  const d = seconds ? 1 : sig(v * 100);
  const td = el(
    "td",
    { class: `num${significant ? "" : " ns"}` },
    el("span", { class: "delta" }, value(v, seconds)),
    el("span", { class: "ci-text cell-ci" }, significant ? range(lo, hi, seconds, d) : "not a finding"),
  );
  if (!significant) td.title = `95% interval ${range(lo, hi, seconds, d)}; not a finding, because bootstrap and regression do not both find an effect`;
  return td;
}

function decompositionTable(data: Data): HTMLElement {
  const rows = new Map(data.tables.decomposition_table.map((r) => [String(r.metric), r]));
  const pool = data.tables.pool_length[0];
  const body = el("tbody");
  for (const g of GROUPS) {
    body.append(el("tr", { class: "group" }, el("th", { scope: "rowgroup", colspan: "5" }, g.name, ...(g.note ? [el("span", { class: "group-note" }, ` · ${g.note}`)] : []))));
    for (const m of g.metrics) {
      const r = rows.get(m.key)!;
      const s = !!m.seconds;
      const name = el("th", { scope: "row", class: "c-metric" }, m.label);
      if (m.primary) name.append(el("span", { class: "tag" }, "primary"));

      const share = num(r, "targeting_share");
      const opposite = Math.sign(num(r, "content")) !== Math.sign(num(r, "targeting"));
      body.append(
        el(
          "tr",
          { class: m.primary ? "primary" : "" },
          name,
          cell(num(r, "total"), num(r, "total_ci_low"), num(r, "total_ci_high"), s, r.total_agree === true),
          cell(num(r, "content"), num(r, "content_ci_low"), num(r, "content_ci_high"), s, r.content_agree === true),
          cell(num(r, "targeting"), num(r, "targeting_ci_low"), num(r, "targeting_ci_high"), s, r.targeting_agree === true),
          opposite
            ? el("td", { class: "num delta" }, "n/a", el("sup", { class: "fn" }, "*"))
            : el("td", { class: "num delta" }, `${Math.round(share * 100)}%`),
        ),
      );
    }
  }
  return el(
    "section",
    { class: "scorecard", "aria-labelledby": "decomp-title" },
    el("h2", { id: "decomp-title" }, "Where each gap comes from"),
    el(
      "p",
      { class: "section-note" },
      "Random minus recommended for the same user on the same day, split into a content part (the random pool's videos) and a targeting part (who they were shown to). Targeting share is the targeting part divided by the whole gap. Grey: not a finding. Both methods must find an effect for it to count.",
    ),
    el(
      "div",
      { class: "table-wrap" },
      el(
        "table",
        { class: "decomp-table" },
        el(
          "thead",
          {},
          el(
            "tr",
            {},
            el("th", { scope: "col", class: "c-metric" }, "Metric"),
            el("th", { scope: "col", class: "num" }, "Whole gap"),
            el("th", { scope: "col", class: "num" }, "Content part"),
            el("th", { scope: "col", class: "num" }, "Targeting part"),
            el("th", { scope: "col", class: "num" }, "Targeting share"),
          ),
        ),
        body,
      ),
    ),
    el(
      "p",
      { class: "figure-note" },
      `* Parts have opposite signs: pool videos are longer (median ${Math.round(num(pool, "pool_median_s"))} s vs ${Math.round(num(pool, "standard_median_s"))} s for other videos, health check 2), so their content part is positive.`,
    ),
  );
}

function hateLine(data: Data): HTMLElement {
  const h = data.tables.hate_facts[0];
  const p3 = (x: number) => pp(x, 3);
  const content = h.c_content_agree === true ? `the videos themselves add ${p3(num(h, "c_content_rise"))}` : `the content part (${p3(num(h, "c_content_rise"))}) is not a finding`;
  return el(
    "section",
    { class: "hate-line", "aria-labelledby": "hate-title" },
    el("h2", { id: "hate-title" }, "Hate"),
    el(
      "p",
      {},
      `Random slots raise hate by ${p3(num(h, "c_total_rise"))}, and most of that, ${p3(num(h, "c_targeting_rise"))} or ${Math.round(num(h, "targeting_share") * 100)}%, comes from targeting; ${content}. `,
      `Comparing the same videos on their own found ${p3(num(h, "b_all"))}, which was too small a sample to tell from zero. On the users in the same-day sample, the same comparison finds ${p3(num(h, "b_on_c_sample"))}, and both methods agree.`,
    ),
  );
}

function bridgeTable(data: Data): HTMLElement {
  const b = data.tables.bridge_effective_view[0];
  const v = (c: string) => pp(num(b, c), Math.abs(num(b, c)) < 0.01 ? 2 : 1);
  const row = (name: string, val: string, step: string) => el("tr", {}, el("th", { scope: "row", class: "c-metric" }, name), el("td", { class: "num" }, val), el("td", { class: "num" }, step));
  return el(
    "div",
    { class: "bridge" },
    el("p", {}, el("strong", {}, "From the same-video comparison to the targeting gap (effective view)."), " The same-video gap and the targeting part differ in who is counted and how they are weighted:"),
    el(
      "div",
      { class: "table-wrap" },
      el(
        "table",
        {},
        el("thead", {}, el("tr", {}, el("th", { scope: "col", class: "c-metric" }, "Step"), el("th", { scope: "col", class: "num" }, "Gap"), el("th", { scope: "col", class: "num" }, "Change"))),
        el(
          "tbody",
          {},
          row(`Same video, all ${num(b, "b_n_videos").toLocaleString("en-US")} pool videos`, v("b_all"), ""),
          row(`Same video, same-day sample (${num(b, "b_on_c_sample_n_videos").toLocaleString("en-US")} videos)`, v("b_on_c_sample"), `${v("sample_part")} sample`),
          row("Targeting part, users weighted equally", v("c_targeting"), `${v("weighting_part")} weighting`),
        ),
      ),
    ),
    el(
      "p",
      {},
      `The same-day sample keeps ${(num(b, "share_random_items_kept") * 100).toFixed(1)}% of random items: user-days where the user also saw a recommended pool video. It leans toward more active users.`,
    ),
  );
}

export const decomposition: Page = {
  path: "/content-vs-targeting",
  nav: "Content vs targeting",
  title: "The same videos do well when they reach the right people",
  question: "Is a random slot costly because the videos are worse, or because they reach the wrong person?",
  data: ["decomposition"],
  notes: [
    "Same video: the random pool's videos were also recommended to some users. Comparing each pool video's rate when recommended with its rate when shown at random holds the video fixed, so the gap is about the audience. Each video counts equally.",
    "Content and targeting: for each user and day, the gap between the user's usual recommended videos and their random videos splits into the gap between usual recommended videos and recommended pool videos (content) and the gap between recommended pool videos and random pool videos (targeting).",
  ],
  dataNotes: (data) => [bridgeTable(data)],
  agreement(data) {
    return data.tables.decomposition_facts[0].effective_view_methods_agree === true ? "Bootstrap and regression agree on the effective-view split" : null;
  },
  render(root, data) {
    const f = data.tables.decomposition_facts[0];
    const gap = (c: string) => pp(num(f, c)).replace("+", "");
    const nVideos = num(data.tables.dumbbell[0], "n_videos");
    const ev = data.tables.dumbbell.find((r) => r.metric === "effective_view")!;
    const panels = el("div", { class: "bells" });
    root.append(
      el(
        "div",
        { class: "lede" },
        el(
          "p",
          {},
          `Of the ${gap("total_gap")} effective-view gap between a user's recommended and random videos, ${gap("targeting_gap")} comes from targeting and only ${gap("content_gap")} from the videos themselves (${Math.round(num(f, "targeting_share") * 100)}% targeting).`,
        ),
      ),
      el(
        "section",
        { class: "hero hero-bells", "aria-labelledby": "bells-title" },
        el(
          "div",
          { class: "hero-main" },
          el("h2", { id: "bells-title" }, "Same video, different audience"),
          el("p", { class: "subtitle" }, `${nVideos.toLocaleString("en-US")} videos shown in both arms`),
          el(
            "p",
            { class: "legend" },
            el("span", { class: "key key-rec", "aria-hidden": "true" }, "●"),
            " Recommended",
            el("span", { class: "key key-rnd", "aria-hidden": "true" }, "○"),
            " Shown at random",
          ),
          panels,
          el(
            "p",
            { class: "figure-note" },
            `For effective view, the same videos reach ${rate(num(ev, "recommended_rate"))} when recommended and ${rate(num(ev, "random_rate"))} at random (${pct(num(ev, "relative"))}). Each video counts equally; the two panels use different scales.`,
          ),
        ),
      ),
      decompositionTable(data),
      hateLine(data),
    );
    let drawn = 0;
    new ResizeObserver(() => {
      const w = panels.clientWidth;
      if (w <= 0 || w === drawn) return;
      drawn = w;
      panels.replaceChildren(
        ...PANELS.map((p) => el("figure", { class: "bell-panel" }, el("figcaption", {}, p.title), dumbbell(data.tables.dumbbell, p.metrics, w))),
      );
    }).observe(panels);
  },
};
