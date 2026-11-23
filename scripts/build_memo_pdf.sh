#!/usr/bin/env bash
# Build docs/memo.pdf from docs/memo.md (D61): writes the appendix chart docs/memo-waterfall.svg from
# the dashboard data, renders the Markdown with marked and the site's Plex fonts, and prints two US Letter
# pages with headless Chrome. Records the SHA-256 of memo.md + the SVG in docs/memo.pdf.source,
# which scripts/check_memo.py recomputes so a stale PDF fails CI.
# Usage: scripts/build_memo_pdf.sh   (needs Node, the dashboard's npm packages and Google Chrome)
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
work="$(mktemp -d)"
trap 'rm -rf -- "${work:?}"' EXIT
node "${repo_root}/dashboard/scripts/memo-html.mjs" "${work}/memo.html"
"${chrome}" --headless=new --disable-gpu --no-pdf-header-footer --allow-file-access-from-files \
  --user-data-dir="${work}/profile" --print-to-pdf="${repo_root}/docs/memo.pdf" "file://${work}/memo.html" 2>/dev/null
cat "${repo_root}/docs/memo.md" "${repo_root}/docs/memo-waterfall.svg" | shasum -a 256 | cut -d' ' -f1 > "${repo_root}/docs/memo.pdf.source"
echo "wrote docs/memo.pdf ($(du -h "${repo_root}/docs/memo.pdf" | cut -f1)) from memo.md $(cut -c1-12 "${repo_root}/docs/memo.pdf.source")"
