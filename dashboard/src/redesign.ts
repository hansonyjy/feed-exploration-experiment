// One scrolling page with numbered sections (D62). Old tab links (#/content-vs-targeting, #/segments,
// #/budget) scroll to their sections. Every number comes from the page JSON; the browser only formats.
import { loadPage, num, type PageFile, type Row } from "./data";
import { pct, pp, sig } from "./format";
import { budget } from "./pages/budget";
import { bridgeTable, decompositionTable } from "./pages/decomposition";
import { howBuilt, scorecard } from "./pages/headline";
import { SHARE_MAX, guardrailChange } from "./simulate";
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
      fig(per100(-num(ev, "estimate")), "fewer good views per 100 random slots than per 100 recommended ones"),
      fig(`${(Math.abs(num(hf, "feed_effective_view_relative")) * 100).toFixed(2)}%`, `of all good views in the feed lost at a ${(num(hf, "top_share") * 100).toFixed(3)}% exploration share`),
      fig(`${Math.round(num(w, "targeting_share") * 100)}%`, "of that loss is targeting: who sees the video, not the video itself", true),
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

// --- Shared: plain horizontal bars (HTML, so labels stay crisp and wrap at any width) ---
type Tone = "accent" | "harm" | "context" | "ghost";

interface Bar {
  label: string;
  value: number;
  text: string;
  tone: Tone;
  title?: string;
}

// One bar group on a shared scale [0, max]; an optional reference line (for example the whole feed).
function bars(rows: Bar[], max: number, ref?: { value: number; label: string }): HTMLElement {
  const box = el("div", { class: "bars", role: "list" });
  rows.forEach((b, i) => {
    const w = `${Math.max(0, (b.value / max) * 100)}%`;
    const track = el("div", { class: "bar-track" }, el("div", { class: `bar-fill tone-${b.tone}`, style: `width:${w}` }));
    if (ref) {
      const line = el("div", { class: "bar-ref", style: `left:${(ref.value / max) * 100}%` });
      if (i === 0) line.append(el("span", { class: "bar-ref-label" }, ref.label));
      track.append(line);
    }
    box.append(
      el(
        "div",
        { class: `bar-row tone-${b.tone}`, role: "listitem", ...(b.title ? { title: b.title } : {}) },
        el("span", { class: "bar-label" }, b.label),
        track,
        el("span", { class: "bar-value" }, b.text),
      ),
    );
  });
  return box;
}

function table(head: string[], body: (string | Node)[][], cls = ""): HTMLElement {
  return el(
    "div",
    { class: "table-wrap" },
    el(
      "table",
      { class: `plain-table ${cls}` },
      el("thead", {}, el("tr", {}, ...head.map((h, i) => el("th", { scope: "col", class: i ? "num" : "c-metric" }, h)))),
      el("tbody", {}, ...body.map((r) => el("tr", {}, ...r.map((c, i) => (i ? el("td", { class: "num" }, c) : el("th", { scope: "row", class: "c-metric" }, c)))))),
    ),
  );
}

const per100 = (x: number, d = 1) => (x * 100).toFixed(d);

// --- 01: two bars a non-expert can read in seconds, plus every other signal as a chip ---
const CHIPS: { key: string; label: string; guardrail?: boolean }[] = [
  { key: "watch_time_ms", label: "Watch time" },
  { key: "naive_completion", label: "Watched to the end" },
  { key: "like_", label: "Likes" },
  { key: "comment_", label: "Comments" },
  { key: "forward_", label: "Shares" },
  { key: "profile_enter", label: "Profile visits" },
  { key: "new_author_follow", label: "Follows of a new creator" },
  { key: "new_category_effective_view", label: "Good views in a new category" },
  { key: "hate", label: "Dislikes", guardrail: true },
  { key: "fast_skip", label: "Skips in under 3 s", guardrail: true },
];

function costChart(data: Data): HTMLElement {
  const by = new Map(data.tables.scorecard.map((r) => [String(r.metric), r]));
  const ev = by.get("effective_view")!;
  const rec = num(ev, "recommended_rate");
  const rnd = num(ev, "random_rate");
  const lost = rnd - rec;
  const row = (label: string, sub: string, cls: string, fill: HTMLElement[], value: string) =>
    el(
      "div",
      { class: `duo-row ${cls}` },
      el("span", { class: "duo-label" }, label, el("span", { class: "duo-sub" }, sub)),
      el("div", { class: "duo-track" }, ...fill),
      el("span", { class: "duo-value" }, value),
    );
  const scale = (x: number) => `${(x / rec) * 100}%`;
  const chart = el(
    "div",
    { class: "duo", role: "img", "aria-label": `Out of 100 views: ${per100(rec)} good views for recommended videos, ${per100(rnd)} for random videos` },
    el("p", { class: "duo-title" }, "Out of every 100 views, how many are good views?"),
    row("Recommended video", "what the app picked for the user", "duo-rec", [el("div", { class: "duo-fill tone-context", style: `width:100%` })], per100(rec)),
    row(
      "Random video",
      "an exploration slot",
      "duo-rnd",
      [
        el("div", { class: "duo-fill tone-accent", style: `width:${scale(rnd)}` }),
        el("div", { class: "duo-lost", style: `left:${scale(rnd)};width:${scale(-lost)}` }, el("span", {}, `${per100(-lost)} fewer (${pct(num(ev, "relative"))})`)),
      ],
      per100(rnd),
    ),
  );
  const chip = (c: (typeof CHIPS)[number]) => {
    const r = by.get(c.key)!;
    const rel = num(r, "relative");
    const up = rel > 0;
    const harm = !!c.guardrail && up;
    return el(
      "li",
      { class: `chip${harm ? " chip-bad" : ""}` },
      el("span", { class: "chip-arrow", "aria-hidden": "true" }, up ? "▲" : "▼"),
      el("span", { class: "chip-label" }, c.label),
      el("span", { class: "chip-value" }, pct(rel)),
    );
  };
  return el(
    "div",
    { class: "story-chart" },
    chart,
    el("p", { class: "chips-title" }, "Every other signal moves the same way (random vs recommended):"),
    el("ul", { class: "chips" }, ...CHIPS.map(chip)),
  );
}

function costSection(data: Data): HTMLElement {
  const ev = data.tables.scorecard.find((r) => r.metric === "effective_view")!;
  return section({
    n: "01",
    id: "cost",
    question: "What does a random slot cost?",
    finding: "A random video gets about a third of the good views a recommended one gets",
    number: `−${per100(-num(ev, "estimate"))}`,
    numberLabel: `good views per 100 random slots (${pp(num(ev, "estimate"), sig(num(ev, "estimate") * 100))}), ${pct(num(ev, "relative"))} vs recommended videos in the same feed`,
    chart: costChart(data),
    howToRead:
      "A good view (an effective view) is one that lasts at least as long as a typical view of a video of similar length. The two bars compare random and recommended videos shown in the same feed request. Red chips are guardrails getting worse.",
    data: scorecard(data),
    about: about(
      [
        "Effective view: watch time at least as long as the median view of videos of similar length.",
        "Comparison: random vs recommended items in the same feed request, each user weighted equally. Intervals come from resampling users (2,000 times), cross-checked with a regression.",
      ],
      data.sources.filter((s) => s.path.includes("comparison_a") || s.path.includes("missing_duration")),
    ),
  });
}

// --- 02: the gap split into two parts; the targeting part is the one accent ---
function whySection(data: Data): HTMLElement {
  const f = one(data, "decomposition_facts");
  const total = num(f, "total_gap");
  const content = num(f, "content_gap");
  const targeting = num(f, "targeting_gap");
  const share = Math.round(num(f, "targeting_share") * 100);
  const w = (x: number) => `${(x / total) * 100}%`;
  const split = el(
    "div",
    { class: "split", role: "img", "aria-label": `${per100(total)} fewer good views per 100: ${per100(content)} from the videos, ${per100(targeting)} from who they were shown to` },
    el("p", { class: "duo-title" }, `Why a random slot gets ${per100(total)} fewer good views per 100`),
    el(
      "div",
      { class: "split-bar" },
      el("div", { class: "split-part tone-context", style: `width:${w(content)}` }),
      el("div", { class: "split-part tone-accent", style: `width:${w(targeting)}` }, el("span", {}, `${per100(targeting)} · ${share}%`)),
    ),
    el(
      "div",
      { class: "split-legend" },
      el("div", { class: "split-key split-key-content" }, el("strong", {}, `${per100(content)} from the videos themselves`), el("span", {}, "The random pool's videos are only a little worse.")),
      el("div", { class: "split-key split-key-targeting" }, el("strong", {}, `${per100(targeting)} from who they were shown to`), el("span", {}, "The same videos do far better when the app picks the viewer.")),
    ),
  );
  const fold = el("div", {}, decompositionTable(data), bridgeTable(data));
  return section({
    n: "02",
    id: "why",
    question: "Why does it cost so much?",
    finding: "The videos are fine; showing them to the wrong people is what costs",
    number: `${share}%`,
    numberLabel: "of the lost good views come from targeting, not from the videos",
    chart: el("div", { class: "story-chart" }, split),
    howToRead:
      "For the same user on the same day, the loss is split in two: how much worse the random pool's videos are when the app recommends them (the videos), and how much is lost by showing them to a random viewer (targeting). Measured on a matched sample, so the total differs a little from section 01.",
    data: fold,
    about: about(
      [
        "Content part: the random pool's videos when recommended, minus other recommended videos. Targeting part: the same pool's videos shown at random, minus when recommended. Sums per user and day, each user weighted equally.",
        "The targeting part is an upper bound on what better targeting could win back.",
      ],
      data.sources.filter((s) => s.path.includes("comparison_c") || s.path.includes("comparison_b") || s.path.includes("bridge")),
    ),
  });
}

// --- 03: segment bars on one scale; the most extreme segment carries the accent (red if harm) ---
const SEG_METRICS: { key: string; label: string; unit: string; loss: boolean }[] = [
  { key: "effective_view", label: "Good views (effective views)", unit: "fewer good views per 100 random slots", loss: true },
  { key: "new_category_effective_view", label: "Good views in a new category", unit: "fewer good views in a new category per 100 random slots", loss: true },
  { key: "fast_skip", label: "Skips in under 3 s", unit: "more fast skips per 100 random slots", loss: false },
  { key: "hate", label: "Dislikes", unit: "more dislikes per 100 random slots", loss: false },
];

const SEG_GROUPS: { key: string; title: string; byValue?: boolean }[] = [
  { key: "category_segment", title: "By type of video", byValue: true },
  { key: "duration_bucket", title: "By video length" },
  { key: "activity_tercile", title: "By how active the user was before" },
];

function digits(max: number): number {
  return max >= 10 ? 1 : max >= 1 ? 2 : 3;
}

function whereSection(data: Data): HTMLElement {
  const labels = new Map(data.tables.segment_labels.map((r) => [`${r.dimension}/${r.segment}`, r]));
  const refs = new Map(data.tables.segment_reference.map((r) => [String(r.metric), r]));
  const c = one(data, "segment_callouts");
  const select = el("select", { id: "seg-metric", class: "control" }, ...SEG_METRICS.map((m) => el("option", { value: m.key }, m.label)));
  const unitLine = el("p", { class: "duo-title" });
  const groups = el("div", { class: "seg-bars" });
  const tableBox = el("div");

  const draw = () => {
    const m = SEG_METRICS.find((x) => x.key === select.value)!;
    const sign = m.loss ? -1 : 1;
    const rows = data.tables.segment_points.filter((r) => r.metric === m.key && SEG_GROUPS.some((g) => g.key === r.dimension) && labels.get(`${r.dimension}/${r.segment}`)!.mixed !== true);
    const shown = (r: Row) => sign * num(r, "estimate");
    const max = Math.max(...rows.map(shown), sign * num(refs.get(m.key)!, "estimate")) * 1.04;
    const d = digits(max * 100);
    const top = rows.reduce((a, b) => (shown(b) > shown(a) ? b : a));
    const ref = sign * num(refs.get(m.key)!, "estimate");
    unitLine.textContent = `${m.unit[0].toUpperCase()}${m.unit.slice(1)}`;
    groups.replaceChildren(
      ...SEG_GROUPS.map((g) => {
        const list: Bar[] = rows
          .filter((r) => r.dimension === g.key)
          .map((r) => {
            const lab = labels.get(`${r.dimension}/${r.segment}`)!;
            const tone: Tone = r === top ? (m.loss ? "accent" : "harm") : "context";
            return { label: String(lab.label), value: shown(r), text: per100(shown(r), d), tone, order: Number(lab.order) } as Bar & { order: number };
          })
          .sort((a, b) => (g.byValue ? b.value - a.value : (a as Bar & { order: number }).order - (b as Bar & { order: number }).order));
        return el("figure", { class: "seg-bar-group" }, el("figcaption", {}, g.title), bars(list, max, { value: ref, label: `whole feed ${per100(ref, d)}` }));
      }),
    );
    tableBox.replaceChildren(
      table(
        ["Segment", "Random minus recommended", "95% interval", "Relative"],
        data.tables.segment_points
          .filter((r) => r.metric === m.key)
          .map((r) => {
            const lab = labels.get(`${r.dimension}/${r.segment}`)!;
            const s = sig(num(r, "estimate") * 100);
            return [String(lab.label), pp(num(r, "estimate"), s), `${pp(num(r, "ci_low"), s)} to ${pp(num(r, "ci_high"), s)}`, pct(num(r, "relative"))];
          }),
      ),
    );
  };
  select.addEventListener("change", draw);
  draw();

  const p1 = (x: number) => (Math.abs(x) * 100).toFixed(1);
  return section({
    n: "03",
    id: "where",
    question: "Where does it hurt most?",
    finding: "What is shown matters more than who sees it",
    number: `${p1(num(c, "worst_estimate"))} vs ${p1(num(c, "best_estimate"))}`,
    numberLabel: `fewer good views per 100 random slots: ${String(c.worst_label).toLowerCase()} vs ${String(c.best_label).toLowerCase()} videos`,
    chart: el(
      "div",
      { class: "story-chart" },
      el("div", { class: "seg-controls" }, el("label", { for: "seg-metric", class: "control-label" }, "Show"), select),
      unitLine,
      groups,
    ),
    howToRead:
      "Longer bars mean a bigger cost. Video type spreads the cost widely; user activity barely moves it. The dashed line is the whole feed. Mixed category groups, formed only for sample size, are in the table, not the chart.",
    data: tableBox,
    about: about(
      [
        "Segments come from data before the test period only (Apr 8 to 21, 2022). Content segments describe the random video; user segments describe the user.",
        "Each segment is compared with the rest of its group, corrected with Benjamini-Hochberg and the stricter Benjamini-Yekutieli. At this sample size nearly every difference passes, so size matters more than significance.",
      ],
      data.sources.filter((s) => s.path.includes("segment") || s.path.includes("merge") || s.path.includes("categor")),
    ),
  });
}

// --- 04: the simulator; the limit line is the accent and only segments past it are red ---
function budgetSection(data: Data): HTMLElement {
  const f = one(data, "budget_facts");
  const host = el("div", { class: "story-chart sim-host" });
  budget.render(host, data);
  host.querySelector(".lede")?.remove();
  const overview = host.querySelector(".overview");
  if (overview) host.prepend(overview);
  const labels = new Map(data.tables.segment_labels.map((r) => [`${r.dimension}/${r.segment}`, String(r.label)]));
  const fine = (x: number) => `${x < 0 ? "−" : "+"}${Math.abs(x * 100).toFixed(2)}%`;
  const rows = data.tables.budget.map((r) => {
    const h = guardrailChange(r, "hate", SHARE_MAX);
    const s = guardrailChange(r, "fast_skip", SHARE_MAX);
    return [labels.get(`${r.dimension}/${r.segment}`) ?? String(r.segment), fine(h.relative), `${fine(h.relativeLow)} to ${fine(h.relativeHigh)}`, fine(s.relative), `${fine(s.relativeLow)} to ${fine(s.relativeHigh)}`];
  });
  return section({
    n: "04",
    id: "budget",
    question: "How much exploration can the feed take?",
    finding: "Up to 1.388% of the feed is safe; random dance videos are not",
    number: `${num(f, "n_no_guardrail_crossed")} of ${num(f, "n_segments")}`,
    numberLabel: "segments stay within both guardrails up to a 1.388% exploration share",
    chart: host,
    howToRead:
      "Each dot is how much a segment's dislike rate rises at a 1.388% exploration share. The teal line is the limit set before the analysis (2% worse). Red dots cross it. Use the controls to try other shares, segments and limits.",
    data: table(["Segment", "Dislikes at 1.388%", "95% interval", "Fast skips at 1.388%", "95% interval"], rows),
    about: about(
      [
        "The simulator assumes a linear effect within the observed range of exploration shares (0.658% to 1.388% of tab-1 impressions). Shares above 1.388% were never observed and need a new test.",
        "Guardrail changes are for the whole feed. User segments use their own recommended rate as the base; content segments use the whole feed's rate.",
      ],
      data.sources.filter((s) => s.path.includes("budget")),
    ),
  });
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
// The sticky nav wraps on narrow screens; sections scroll to just below it.
function setNavHeight(): void {
  const nav = document.getElementById("nav-host");
  if (nav) document.documentElement.style.setProperty("--nav-h", `${nav.offsetHeight + 8}px`);
}

export function scrollToHash(): void {
  setNavHeight();
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
  root.replaceChildren(
    strip(data, one(data, "headline_facts").all_methods_agree === true ? `Bootstrap and regression agree on all ${num(one(data, "headline_facts"), "n_metrics")} metrics` : null),
    hero(data),
    costSection(data),
    whySection(data),
    whereSection(data),
    budgetSection(data),
    howBuilt(one(data, "build_facts")),
  );
  // Charts size themselves after layout and fonts; scroll once they have settled.
  new ResizeObserver(setNavHeight).observe(navHost);
  void document.fonts.ready.then(() => setTimeout(scrollToHash, 60));
}
