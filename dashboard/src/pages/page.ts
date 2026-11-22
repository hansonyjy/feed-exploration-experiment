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

// Experiment header strip on every page: who and what was measured, from Comparison A's main row.
function strip(data: Data, agreement: string | null): HTMLElement {
  const main = data.tables.comparison_a.find(
    (r) => r.analysis === "A_request" && r.variant === "main" && r.weighting === "equal_user" && r.metric === "effective_view",
  )!;
  const item = (k: string, v: string | Node) => el("div", { class: "strip-item" }, el("span", { class: "strip-k" }, k), el("span", { class: "strip-v" }, v));
  const badge = link(PREREG, "Pre-registered");
  badge.className = "badge";
  badge.title = "Metrics, tests and parameters were fixed before any outcome was read (git tag prereg-v1)";
  return el(
    "div",
    { class: "strip", role: "group", "aria-label": "Experiment summary" },
    item("Users", compact(num(main, "n_users"))),
    item("Random requests", compact(num(main, "n_units"))),
    item("Window", "Apr 23 to May 8, 2022"),
    item("Surface", "Tab 1 feed"),
    el("div", { class: "strip-flags" }, badge, ...(agreement ? [el("span", { class: "agree" }, agreement)] : [])),
  );
}

// Shell shared by every page: header strip, title (the answer), content, About drawer.
export async function renderPage(page: Page, root: HTMLElement): Promise<void> {
  root.replaceChildren();
  const body = el("div", { class: "page-body", "aria-busy": "true" }, el("p", { class: "muted" }, "Loading data…"));
  root.append(body);
  try {
    const files = [...new Set<PageFile>(["headline", ...page.data])];
    const data = merge(await Promise.all(files.map(loadPage)));
    body.replaceChildren();
    body.removeAttribute("aria-busy");
    root.prepend(strip(data, page.agreement ? page.agreement(data) : null), el("h1", {}, page.title));
    page.render(body, data);
    root.append(about([el("p", {}, el("strong", {}, "Question: "), page.question), ...page.notes], data.sources));
  } catch (err) {
    body.replaceChildren(el("p", { class: "error", role: "alert" }, `Could not load data: ${(err as Error).message}`));
  }
}
