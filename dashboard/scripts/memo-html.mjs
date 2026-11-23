// Render docs/memo.md to a print-ready HTML page for scripts/build_memo_pdf.sh, and write the appendix
// chart docs/memo-waterfall.svg from exports/dashboard/headline.json (the page 1 waterfall's numbers).
// Usage: node memo-html.mjs <out.html>
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { marked } from "marked";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));

// --- Waterfall SVG (recommended rate, content gap, targeting gap, random rate) from headline.json ---
const page = JSON.parse(readFileSync(here("../../exports/dashboard/headline.json"), "utf-8"));
const wt = page.tables.waterfall;
const w = Object.fromEntries(wt.columns.map((c, i) => [c, wt.rows[0][i]]));
const rec = w.recommended_rate;
const content = w.content_gap;
const targeting = w.targeting_gap;
const random = w.random_rate;
const pct = (x) => `${(x * 100).toFixed(1)}%`;
const pp = (x) => `−${(x * 100).toFixed(1)} pp`;
const W = 520, H = 210, L = 40, B = 28, T = 22, max = 0.6;
const y = (v) => T + (1 - v / max) * (H - T - B);
const bw = 70, gap = (W - L - 4 * bw) / 4;
const x = (i) => L + gap / 2 + i * (bw + gap);
const bars = [
  { label: "Recommended", y1: 0, y2: rec, value: pct(rec), fill: "#4b515c" },
  { label: "Content gap", y1: rec - content, y2: rec, value: pp(content), fill: "#8b919c" },
  { label: "Targeting gap", y1: random, y2: rec - content, value: pp(targeting), fill: "#3155d6" },
  { label: "Random", y1: 0, y2: random, value: pct(random), fill: "#4b515c" },
];
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" font-family="IBM Plex Sans, Helvetica, Arial, sans-serif" font-size="11">
${[0, 0.2, 0.4, 0.6].map((t) => `<line x1="${L}" x2="${W}" y1="${y(t)}" y2="${y(t)}" stroke="#e6e7ea"/><text x="${L - 6}" y="${y(t) + 4}" text-anchor="end" fill="#8b919c">${Math.round(t * 100)}%</text>`).join("\n")}
${bars.map((b, i) => `<rect x="${x(i)}" y="${y(b.y2)}" width="${bw}" height="${y(b.y1) - y(b.y2)}" fill="${b.fill}"/><text x="${x(i) + bw / 2}" y="${y(b.y2) - 6}" text-anchor="middle" fill="#15171b" font-weight="600">${b.value}</text><text x="${x(i) + bw / 2}" y="${H - 10}" text-anchor="middle" fill="#4b515c">${b.label}</text>`).join("\n")}
<line x1="${x(0) + bw}" x2="${x(1)}" y1="${y(rec)}" y2="${y(rec)}" stroke="#8b919c" stroke-dasharray="3,3"/>
<line x1="${x(1) + bw}" x2="${x(2)}" y1="${y(rec - content)}" y2="${y(rec - content)}" stroke="#8b919c" stroke-dasharray="3,3"/>
<line x1="${x(2) + bw}" x2="${x(3)}" y1="${y(random)}" y2="${y(random)}" stroke="#8b919c" stroke-dasharray="3,3"/>
</svg>
`;
writeFileSync(here("../../docs/memo-waterfall.svg"), svg);

// --- Memo HTML ---
const md = readFileSync(here("../../docs/memo.md"), "utf-8");
const font = (pkg, file) => pathToFileURL(here(`../node_modules/@fontsource/${pkg}/files/${file}`)).href;
// Relative links and images resolve on GitHub (links) or next to the memo (the SVG).
const REPO = "https://github.com/hansonyjy/feed-exploration-experiment/blob/main/docs/";
marked.use({
  walkTokens: (t) => {
    if (t.type === "link" && !/^https?:/.test(t.href)) t.href = new URL(t.href, REPO).href;
    if (t.type === "image") t.href = pathToFileURL(here(`../../docs/${t.href}`)).href;
  },
});
const body = marked.parse(md);
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Exploration budget: decision memo</title>
<style>
@font-face { font-family: "Plex Sans"; src: url("${font("ibm-plex-sans", "ibm-plex-sans-latin-400-normal.woff2")}"); font-weight: 400; }
@font-face { font-family: "Plex Sans"; src: url("${font("ibm-plex-sans", "ibm-plex-sans-latin-600-normal.woff2")}"); font-weight: 600; }
@font-face { font-family: "Plex Mono"; src: url("${font("ibm-plex-mono", "ibm-plex-mono-latin-400-normal.woff2")}"); font-weight: 400; }
@page { size: Letter; margin: 0.42in 0.5in; }
body { font: 10pt/1.22 "Plex Sans", sans-serif; color: #15171b; font-variant-numeric: tabular-nums; }
h1 { font-size: 15pt; font-weight: 600; margin: 0 0 1pt; letter-spacing: -0.01em; }
h1 + p { color: #6b717c; margin: 0 0 5pt; font-size: 9pt; }
h2 { font-size: 10.5pt; font-weight: 600; margin: 5pt 0 1pt; padding-top: 3pt; border-top: 0.5pt solid #c8ccd3; }
h3 { font-size: 10pt; font-weight: 600; margin: 7pt 0 2pt; }
p, li { margin: 1pt 0; }
ul, ol { padding-left: 14pt; margin: 1.5pt 0; }
strong { font-weight: 600; }
.tags { color: #6b717c; font-size: 8pt; margin-left: 4pt; white-space: nowrap; }
table { border-collapse: collapse; margin: 2pt 0; }
th, td { text-align: left; padding: 0.5pt 12pt 0.5pt 0; border-bottom: 0.5pt solid #e6e7ea; }
th { color: #6b717c; font-weight: 400; }
code { font-family: "Plex Mono", monospace; font-size: 9pt; }
a { color: #2645b8; text-decoration: none; }
img { width: 4.6in; height: auto; display: block; margin: 2pt 0; }
.page-break { break-before: page; }
</style></head><body>${body}</body></html>`;
writeFileSync(process.argv[2], html);
