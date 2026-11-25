// One scrolling page with numbered sections (D62). Old tab links (#/content-vs-targeting, #/segments,
// #/budget) scroll to their sections. Every number comes from the page JSON; the browser only formats.
import * as Plot from "@observablehq/plot";
import { loadPage, num, type PageFile, type Row } from "./data";
import { pct, pp, sig } from "./format";
import { scorecard } from "./pages/headline";
import { merge, strip, type Data } from "./pages/page";
import { about, el, repoLink } from "./ui";

export const SECTIONS = [
  { n: "01", id: "cost", hash: "#/cost", title: "What a random slot costs" },
  { n: "02", id: "why", hash: "#/content-vs-targeting", title: "Why: targeting, not content" },
  { n: "03", id: "where", hash: "#/segments", title: "Where it hurts most" },
  { n: "04", id: "budget", hash: "#/budget", title: "How much exploration the feed can take" },
] as const;

const one = (data: Data, table: string): Row => data.tables[table][0];

// --- Hero: the answer, one line of context, four key figures (one carries the accent) ---
function hero(data: Data): HTMLElement {
  const ev = data.tables.scorecard.find((r) => r.metric === "effective_view")!;
  const hf = one(data, "headline_facts");
  const w = one(data, "waterfall");
  const fig = (value: string, label: string, accent = false) =>
    el("div", { class: `figure${accent ? " figure-accent" : ""}` }, el("span", { class: "figure-value" }, value), el("span", { class: "figure-label" }, label));
  return el(
    "header",
    { class: "lead", id: "top" },
    el("h1", {}, "Exploration's real cost is bad targeting, not bad videos"),
    el(
      "p",
      { class: "lead-context" },
      "In KuaiRand, a public log of a short-video app, some feed requests showed a random video instead of a recommended one. Each random slot is a measured exploration slot.",
    ),
    el(
      "p",
      { class: "lead-links" },
      repoLink("docs/memo.pdf", "Decision memo (PDF)"),
      " · ",
      el("a", { href: `${import.meta.env.BASE_URL}dbt/` }, "Data models"),
      " · ",
      repoLink("docs/findings.md", "Findings"),
    ),
    el(
      "div",
      { class: "figures" },
      fig(pp(num(ev, "estimate"), 1).replace("+", ""), "effective views lost in a random slot, per slot"),
      fig(`${(Math.abs(num(hf, "feed_effective_view_relative")) * 100).toFixed(2)}%`, `of the feed's effective views lost at a ${(num(hf, "top_share") * 100).toFixed(3)}% exploration share`),
      fig(`${Math.round(num(w, "targeting_share") * 100)}%`, "of the per-slot loss is targeting: who sees the video, not the video", true),
      fig("Hold", "both guardrails at that share, except for dance videos"),
    ),
  );
}

// --- Section pattern: question label, finding headline, hero number, chart, how to read, details ---
interface SectionParts {
  n: string;
  id: string;
  question: string;
  finding: string;
  number: string;
  numberLabel: string;
  chart: HTMLElement;
  howToRead: string;
  data: HTMLElement;
  about: HTMLElement;
}

function section(p: SectionParts): HTMLElement {
  const dataBox = el("details", { class: "fold" }, el("summary", {}, "Show the data"), p.data);
  return el(
    "section",
    { class: "story", id: p.id, "aria-labelledby": `${p.id}-title` },
    el("p", { class: "story-label" }, el("span", { class: "story-n" }, p.n), p.question),
    el(
      "div",
      { class: "story-head" },
      el("h2", { id: `${p.id}-title` }, p.finding),
      el("div", { class: "story-number" }, el("span", { class: "story-number-value" }, p.number), el("span", { class: "story-number-label" }, p.numberLabel)),
    ),
    p.chart,
    el("p", { class: "how-to-read" }, el("strong", {}, "How to read this: "), p.howToRead),
    dataBox,
    p.about,
  );
}

// --- 01: relative change for every metric; the primary metric carries the accent ---
const METRICS: { key: string; label: string; group: string; primary?: boolean; guardrail?: boolean }[] = [
  { key: "effective_view", label: "Effective view", group: "Engagement", primary: true },
  { key: "naive_completion", label: "Completed view", group: "Engagement" },
  { key: "watch_time_ms", label: "Watch time", group: "Engagement" },
  { key: "like_", label: "Like", group: "Engagement" },
  { key: "comment_", label: "Comment", group: "Engagement" },
  { key: "forward_", label: "Share", group: "Engagement" },
  { key: "profile_enter", label: "Profile visit", group: "Engagement" },
  { key: "new_author_follow", label: "Follow a new creator", group: "Discovery" },
  { key: "new_category_effective_view", label: "Effective view, new category", group: "Discovery" },
  { key: "hate", label: "Hate (dislike button)", group: "Guardrails, higher is worse", guardrail: true },
  { key: "fast_skip", label: "Fast skip (under 3 s)", group: "Guardrails, higher is worse", guardrail: true },
];

interface Dot {
  label: string;
  value: number;
  low: number;
  high: number;
  kind: "accent" | "harm" | "context";
  text: string;
}

function costChart(data: Data, width: number): HTMLElement {
  const by = new Map(data.tables.scorecard.map((r) => [String(r.metric), r]));
  const narrow = width < 640;
  const domain: [number, number] = [-1, 1.5];
  const groups = [...new Set(METRICS.map((m) => m.group))];
  const box = el("div", { class: "chart-groups" });
  for (const g of groups) {
    const dots: Dot[] = METRICS.filter((m) => m.group === g).map((m) => {
      const r = by.get(m.key)!;
      const value = num(r, "relative");
      const kind = m.primary ? "accent" : m.guardrail && value > 0 ? "harm" : "context";
      return { label: m.label, value, low: num(r, "relative_ci_low"), high: num(r, "relative_ci_high"), kind, text: pct(value) };
    });
    const color = (d: Dot) => (d.kind === "accent" ? "var(--accent)" : d.kind === "harm" ? "var(--bad)" : "var(--context-ink)");
    const primary = dots.filter((d) => d.kind === "accent");
    const marks: Plot.Markish[] = [
      Plot.gridX({ stroke: "var(--rule)", strokeOpacity: 1, ticks: [-1, -0.5, 0, 0.5, 1, 1.5] }),
      Plot.ruleX([0], { stroke: "var(--ink-3)" }),
      Plot.ruleY(dots, { y: "label", x1: "low", x2: "high", stroke: color, strokeWidth: 2 }),
      Plot.dot(dots, { y: "label", x: "value", fill: color, r: (d: Dot) => (d.kind === "accent" ? 6 : 4) }),
      // Values just right of each interval (clear of the row labels); the accent row in bold.
      ...([true, false] as const).map((bold) =>
        Plot.text(dots.filter((d) => (d.kind === "accent") === bold), {
          y: "label",
          x: "high",
          dx: 8,
          textAnchor: "start",
          text: "text",
          fill: (d: Dot) => (d.kind === "context" ? "var(--ink-3)" : color(d)),
          fontWeight: bold ? 700 : 400,
        }),
      ),
    ];
    if (primary.length && !narrow) {
      // Annotation with a leader line from the primary dot to its note, in the empty space to the right.
      marks.push(
        Plot.link(primary, { y1: "label", y2: "label", x1: (d: Dot) => d.high + 0.17, x2: () => 0.25, stroke: "var(--accent)", strokeWidth: 1 }),
        Plot.text(primary, { y: "label", x: () => 0.27, textAnchor: "start", text: () => "The primary metric: a random slot gets about a third of the effective views", fill: "var(--accent-ink)", fontSize: 13, lineWidth: 26 }),
      );
    }
    const plot = Plot.plot({
      width,
      height: dots.length * 30 + (g === groups[0] ? 34 : 14),
      marginLeft: narrow ? 128 : 220,
      marginRight: 16,
      marginTop: g === groups[0] ? 26 : 6,
      marginBottom: 8,
      style: { fontFamily: "var(--sans)", fontSize: narrow ? "11px" : "13px" },
      x: { domain, label: null, axis: g === groups[0] ? "top" : null, ticks: [-1, -0.5, 0, 0.5, 1, 1.5], tickFormat: (d: number) => (d === 0 ? "0" : pct(d)) },
      y: { domain: dots.map((d) => d.label), label: null, tickSize: 0, tickPadding: 10 },
      marks,
    });
    box.append(el("figure", { class: "chart-group" }, el("figcaption", {}, g), plot));
  }
  return box;
}

function costSection(data: Data): HTMLElement {
  const ev = data.tables.scorecard.find((r) => r.metric === "effective_view")!;
  const chart = el("div", { class: "story-chart" });
  let drawn = 0;
  new ResizeObserver(() => {
    const w = chart.clientWidth;
    if (w > 0 && w !== drawn) {
      drawn = w;
      chart.replaceChildren(costChart(data, w));
    }
  }).observe(chart);
  return section({
    n: "01",
    id: "cost",
    question: "What does a random slot cost?",
    finding: "A random slot gets far fewer effective views than a recommended one, and every engagement metric falls",
    number: pp(num(ev, "estimate"), sig(num(ev, "estimate") * 100)),
    numberLabel: `effective views, ${pct(num(ev, "relative"))} of the recommended rate`,
    chart,
    howToRead: "Each dot is a random slot's rate relative to a recommended slot in the same feed request; the line is the 95% interval. Only guardrails that get worse are red.",
    data: scorecard(data),
    about: about(
      [
        "Effective view: watch time at least as long as the median view of videos of similar length.",
        "Comparison: random vs recommended items in the same feed request, each user weighted equally. Intervals come from resampling users (2,000 times), cross-checked with a regression.",
      ],
      data.sources,
    ),
  });
}

function placeholder(s: (typeof SECTIONS)[number]): HTMLElement {
  return el(
    "section",
    { class: "story story-pending", id: s.id },
    el("p", { class: "story-label" }, el("span", { class: "story-n" }, s.n), s.title),
    el("p", { class: "muted" }, "This section is rebuilt in the new pattern after the palette is chosen."),
  );
}

function nav(): HTMLElement {
  return el(
    "nav",
    { class: "section-nav", "aria-label": "Sections" },
    el("a", { href: "#/", class: "section-nav-home" }, "Feed exploration budget"),
    el("ol", {}, ...SECTIONS.map((s) => el("li", {}, el("a", { href: s.hash }, el("span", { class: "nav-n" }, s.n), el("span", { class: "nav-t" }, s.title))))),
  );
}

// Old tab hashes and new section hashes both scroll to their section.
export function scrollToHash(): void {
  const h = location.hash || "#/";
  const s = SECTIONS.find((x) => x.hash === h);
  if (!s) {
    window.scrollTo(0, 0);
    return;
  }
  document.getElementById(s.id)?.scrollIntoView({ block: "start" });
}

export async function renderStory(root: HTMLElement, navHost: HTMLElement): Promise<void> {
  navHost.replaceChildren(nav());
  const files: PageFile[] = ["headline", "decomposition", "segments", "budget"];
  const data = merge(await Promise.all(files.map(loadPage)));
  const headlineData: Data = { tables: data.tables, sources: data.sources.filter((s) => s.path.includes("comparison_a") || s.path.includes("missing_duration")) };
  root.replaceChildren(
    strip(data, one(data, "headline_facts").all_methods_agree === true ? `Bootstrap and regression agree on all ${num(one(data, "headline_facts"), "n_metrics")} metrics` : null),
    hero(data),
    costSection(headlineData),
    ...SECTIONS.slice(1).map(placeholder),
  );
  requestAnimationFrame(scrollToHash);
}
