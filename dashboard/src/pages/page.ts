import { loadPage, type PageData, type PageFile } from "../data";
import { about, dataLink, el, placeholder } from "../ui";

export interface Page {
  path: string;
  nav: string;
  title: string;
  question: string;
  data: PageFile;
  due: string;
  notes: string[];
  render?: (root: HTMLElement, data: PageData) => void;
}

// Shell shared by every page: title, the one question it answers, its content, and the About drawer.
export async function renderPage(page: Page, root: HTMLElement): Promise<void> {
  root.replaceChildren(
    el("p", { class: "eyebrow" }, page.nav),
    el("h1", {}, page.title),
    el("p", { class: "question" }, page.question),
  );
  const body = el("div", { class: "page-body", "aria-busy": "true" }, el("p", { class: "muted" }, "Loading data…"));
  root.append(body);
  try {
    const data = await loadPage(page.data);
    body.replaceChildren();
    body.removeAttribute("aria-busy");
    if (page.render) page.render(body, data);
    else body.append(placeholder(`This view is being built and lands ${page.due}.`));
    body.append(sourceList(data));
    root.append(about(page.notes, Object.values(data.sources).map((s) => s.path)));
  } catch (err) {
    body.replaceChildren(el("p", { class: "error", role: "alert" }, `Could not load data: ${(err as Error).message}`));
  }
}

function sourceList(data: PageData): HTMLElement {
  const rows = Object.values(data.sources).map((s) =>
    el("li", {}, dataLink(s.path), ` · ${s.rows_kept.toLocaleString("en-US")} rows`),
  );
  return el("section", { class: "sources" }, el("h2", {}, "Data loaded for this view"), el("ul", {}, ...rows));
}
