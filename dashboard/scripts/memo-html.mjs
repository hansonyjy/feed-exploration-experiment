// Render docs/memo.md to a print-ready HTML page for scripts/build_memo_pdf.sh. Usage: node memo-html.mjs <out.html>
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { marked } from "marked";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const md = readFileSync(here("../../docs/memo.md"), "utf-8");
const font = (pkg, file) => pathToFileURL(here(`../node_modules/@fontsource/${pkg}/files/${file}`)).href;
// Relative links (findings.md, ...) point at the files on GitHub, so they work in the downloaded PDF.
const REPO = "https://github.com/hansonyjy/feed-exploration-experiment/blob/main/docs/";
marked.use({ walkTokens: (t) => { if (t.type === "link" && !/^https?:/.test(t.href)) t.href = REPO + t.href; } });
const body = marked.parse(md);
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Exploration budget: decision memo</title>
<style>
@font-face { font-family: "Plex Sans"; src: url("${font("ibm-plex-sans", "ibm-plex-sans-latin-400-normal.woff2")}"); font-weight: 400; }
@font-face { font-family: "Plex Sans"; src: url("${font("ibm-plex-sans", "ibm-plex-sans-latin-600-normal.woff2")}"); font-weight: 600; }
@font-face { font-family: "Plex Mono"; src: url("${font("ibm-plex-mono", "ibm-plex-mono-latin-400-normal.woff2")}"); font-weight: 400; }
@page { size: A4; margin: 10mm 15mm; }
body { font: 8.7pt/1.32 "Plex Sans", sans-serif; color: #15171b; font-variant-numeric: tabular-nums; }
h1 { font-size: 15pt; font-weight: 600; margin: 0 0 2pt; letter-spacing: -0.01em; }
h1 + p { color: #6b717c; margin: 0 0 10pt; font-size: 9pt; }
h2 { font-size: 10pt; font-weight: 600; margin: 6pt 0 2pt; padding-top: 4pt; border-top: 0.5pt solid #c8ccd3; }
p, li { margin: 2pt 0; }
ul, ol { padding-left: 15pt; margin: 3pt 0; }
strong { font-weight: 600; }
table { border-collapse: collapse; margin: 4pt 0; font-size: 8.8pt; }
th, td { text-align: left; padding: 1.5pt 10pt 1.5pt 0; border-bottom: 0.5pt solid #e6e7ea; }
th { color: #6b717c; font-weight: 400; }
code { font-family: "Plex Mono", monospace; font-size: 9pt; }
a { color: #2645b8; text-decoration: none; }
</style></head><body>${body}</body></html>`;
writeFileSync(process.argv[2], html);
