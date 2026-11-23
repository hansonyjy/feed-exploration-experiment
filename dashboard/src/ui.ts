// Small DOM helpers and the "About this view" drawer every page carries (D61).
import type { Source } from "./data";

const REPO = "https://github.com/hansonyjy/feed-exploration-experiment";

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

// Pinned to the commit the site was built from (see vite.config.ts).
export function repoLink(path: string, text = path): HTMLAnchorElement {
  return link(`${REPO}/blob/${__COMMIT__}/${path}`, text);
}

export function dataLink(path: string): HTMLAnchorElement {
  // Exports are published next to the site, so each can be downloaded as is; seeds link to GitHub.
  if (!path.startsWith("exports/")) return repoLink(path);
  return link(`${import.meta.env.BASE_URL}${path.replace(/^exports\//, "")}`, path);
}

export function about(notes: (Node | string)[], sources: Source[]): HTMLDetailsElement {
  const unique = [...new Map(sources.map((s) => [s.path, s])).values()];
  const list = el("ul", { class: "sources" });
  for (const s of unique) {
    list.append(el("li", {}, dataLink(s.path), ` · ${s.rows_kept.toLocaleString("en-US")} rows`));
  }
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
      repoLink("docs/data_quality.md", "data quality checks"),
      " · ",
      repoLink("docs/analysis_plan.md", "pre-registered plan"),
      ".",
    ),
  );
}

export interface KeyNumber {
  value: string;
  label: string;
}

// Numbers (with their units) in Plex Mono, connecting words ("of", "vs") in Plex Sans.
const CONNECTORS = new Set(["of", "vs", "to", "and"]);
function readoutValue(value: string): HTMLElement {
  const out = el("span", { class: "readout-value" });
  value.split(" ").forEach((tok, i) => {
    if (i > 0) out.append(" ");
    out.append(el("span", { class: CONNECTORS.has(tok) ? "readout-word" : "readout-num" }, tok));
  });
  return out;
}

// Pages still being built: one finding, one key number, the due date in small text.
export function preview(finding: string, key: KeyNumber, due: string): HTMLElement {
  return el(
    "section",
    { class: "preview" },
    el("p", { class: "finding" }, finding),
    el("div", { class: "readout" }, readoutValue(key.value), el("span", { class: "readout-label" }, key.label)),
    el("p", { class: "due" }, `The full interactive view lands ${due}.`),
  );
}

// Chart labels on narrow screens: keep mixed category groups' numbers visible, truncate the rest.
export function chartLabel(label: string, narrow: boolean, max: number): string {
  if (narrow) label = label.replace(/^Mixed category group (\d+) \(not interpreted\)$/, "Mixed group $1");
  return label.length > max ? `${label.slice(0, max - 1)}…` : label;
}
