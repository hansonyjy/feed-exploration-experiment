#!/usr/bin/env bash
# Build docs/memo.pdf from docs/memo.md (D61): marked renders the Markdown to HTML with the site's
# Plex fonts, headless Chrome prints it to A4. Records the memo's SHA-256 in docs/memo.pdf.source,
# which scripts/check_memo.py compares against memo.md so a stale PDF fails CI.
# Usage: scripts/build_memo_pdf.sh   (needs Node, the dashboard's npm packages and Google Chrome)
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
work="$(mktemp -d)"
trap 'rm -rf -- "${work:?}"' EXIT
node "${repo_root}/dashboard/scripts/memo-html.mjs" "${work}/memo.html"
"${chrome}" --headless=new --disable-gpu --no-pdf-header-footer --allow-file-access-from-files \
  --user-data-dir="${work}/profile" --print-to-pdf="${repo_root}/docs/memo.pdf" "file://${work}/memo.html" 2>/dev/null
shasum -a 256 "${repo_root}/docs/memo.md" | cut -d' ' -f1 > "${repo_root}/docs/memo.pdf.source"
echo "wrote docs/memo.pdf ($(du -h "${repo_root}/docs/memo.pdf" | cut -f1)) from memo.md $(cut -c1-12 "${repo_root}/docs/memo.pdf.source")"
