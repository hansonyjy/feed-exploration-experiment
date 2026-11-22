import { loadPage, num, type PageData, type PageFile, type Row, type Source } from "../data";
import { about, el, link } from "../ui";

export interface Data {
  tables: Record<string, Row[]>;
  sources: Source[];
}

export interface Page {
  path: string;
  nav: string;
  title: string;
  question: string;
  data: PageFile[];
  notes: string[];
  // Text for the header strip when both inference methods agree on this page's results, else null.
  agreement?: (data: Data) => string | null;
  // Plain note shown in the strip instead of an agreement line (no check mark).
  stripNote?: string;
  render: (root: HTMLElement, data: Data) => void;
}

const PREREG = "https://github.com/hansonyjy/feed-exploration-experiment/tree/prereg-v1";

function merge(pages: PageData[]): Data {
  const tables: Record<string, Row[]> = {};
  const sources: Source[] = [];
  for (const p of pages) {
    Object.assign(tables, p.tables);
    sources.push(...Object.values(p.sources));
  }
  return { tables, sources };
}

function compact(n: number): string {
  return n >= 1e6 ? `${(n / 1e6).toFixed(2)}M` : n.toLocaleString("en-US");
}

// Experiment header strip on every page: who and what was measured (headline_facts, from Comparison A).
function strip(data: Data, agreement: string | null, note?: string): HTMLElement {
  const main = data.tables.headline_facts[0];
  const item = (k: string, v: string | Node) => el("div", { class: "strip-item" }, el("span", { class: "strip-k" }, k), el("span", { class: "strip-v" }, v));
  const badge = link(PREREG, "Pre-registered");
  badge.className = "badge";
  badge.title = "Metrics, tests and parameters were fixed before any outcome was read (git tag prereg-v1)";
  return el(
    "div",
    { class: "strip", role: "group", "aria-label": "Experiment summary" },
    item("Users", compact(num(main, "n_users"))),
    item("Random requests", compact(num(main, "n_random_requests"))),
    item("Window", "Apr 23 to May 8, 2022"),
    item("Surface", "Tab 1 feed"),
    badge,
    ...(agreement ? [el("span", { class: "agree" }, agreement)] : []),
    ...(note ? [el("span", { class: "strip-note" }, note)] : []),
  );
}

// Shell shared by every page: header strip, title (the answer), content, About drawer.
let current = 0; // the latest navigation; an older load that finishes later must not draw

export async function renderPage(page: Page, root: HTMLElement): Promise<void> {
  const token = ++current;
  root.replaceChildren();
  const body = el("div", { class: "page-body", "aria-busy": "true" }, el("p", { class: "muted" }, "Loading data…"));
  root.append(body);
  try {
    const files = [...new Set<PageFile>(["headline", ...page.data])];
    const data = merge(await Promise.all(files.map(loadPage)));
    if (token !== current) return;
    body.replaceChildren();
    body.removeAttribute("aria-busy");
    root.prepend(strip(data, page.agreement ? page.agreement(data) : null, page.stripNote), el("h1", {}, page.title));
    page.render(body, data);
    root.append(about([el("p", {}, el("strong", {}, "Question: "), page.question), ...page.notes], data.sources));
  } catch (err) {
    if (token !== current) return;
    body.replaceChildren(el("p", { class: "error", role: "alert" }, `Could not load data: ${(err as Error).message}`));
  }
}
