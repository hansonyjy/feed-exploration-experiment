// Small DOM helpers and the "About this view" drawer every page carries (D61).

const REPO = "https://github.com/hansonyjy/feed-exploration-experiment/blob/main";

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, string> = {},
  ...children: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  node.append(...children);
  return node;
}

export function link(href: string, text: string): HTMLAnchorElement {
  return el("a", { href }, text);
}

export function repoLink(path: string, text = path): HTMLAnchorElement {
  return link(`${REPO}/${path}`, text);
}

export function dataLink(path: string): HTMLAnchorElement {
  // Exports are published next to the site, so each can be downloaded as is; seeds link to GitHub.
  if (!path.startsWith("exports/")) return repoLink(path);
  return link(`${import.meta.env.BASE_URL}${path.replace(/^exports\//, "")}`, path);
}

export function about(notes: (Node | string)[], sources: string[]): HTMLDetailsElement {
  const list = el("ul");
  for (const s of sources) list.append(el("li", {}, dataLink(s)));
  return el(
    "details",
    { class: "about" },
    el("summary", {}, "About this view"),
    ...notes.map((n) => (typeof n === "string" ? el("p", {}, n) : n)),
    el("p", {}, "Data behind this view:"),
    list,
    el(
      "p",
      {},
      "Full record: ",
      repoLink("docs/findings.md", "findings"),
      " · ",
      repoLink("docs/decisions.md", "decision log"),
      " · ",
      repoLink("docs/data_quality.md", "data quality and health checks"),
      " · ",
      repoLink("docs/analysis_plan.md", "pre-registered plan"),
      ".",
    ),
  );
}

export function placeholder(text: string): HTMLElement {
  return el("div", { class: "placeholder", role: "note" }, text);
}
