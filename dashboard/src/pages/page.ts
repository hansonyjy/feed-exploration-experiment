import { loadPage, type PageData, type PageFile, type Row, type Source } from "../data";
import { about, el } from "../ui";

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
  render: (root: HTMLElement, data: Data) => void;
}

function merge(pages: PageData[]): Data {
  const tables: Record<string, Row[]> = {};
  const sources: Source[] = [];
  for (const p of pages) {
    Object.assign(tables, p.tables);
    sources.push(...Object.values(p.sources));
  }
  return { tables, sources };
}

// Shell shared by every page: title (the answer), the question it answers, content, About drawer.
export async function renderPage(page: Page, root: HTMLElement): Promise<void> {
  root.replaceChildren(el("p", { class: "eyebrow" }, page.nav), el("h1", {}, page.title));
  const body = el("div", { class: "page-body", "aria-busy": "true" }, el("p", { class: "muted" }, "Loading data…"));
  root.append(body);
  try {
    const data = merge(await Promise.all(page.data.map(loadPage)));
    body.replaceChildren();
    body.removeAttribute("aria-busy");
    page.render(body, data);
    root.append(about([el("p", {}, el("strong", {}, "Question: "), page.question), ...page.notes], data.sources));
  } catch (err) {
    body.replaceChildren(el("p", { class: "error", role: "alert" }, `Could not load data: ${(err as Error).message}`));
  }
}
