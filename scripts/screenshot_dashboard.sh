#!/usr/bin/env bash
# Regenerate docs/img/dashboard-page1.png for the README: build the dashboard, serve the built site
# locally, and capture page 1 (header strip, waterfall and decision) with headless Chrome, light mode.
# Usage: scripts/screenshot_dashboard.sh   (needs Node, the dashboard's npm packages and Google Chrome)
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
port=4179
work="$(mktemp -d)"
cd "${repo_root}/dashboard"
npm run build --silent >/dev/null
npx vite preview --port "${port}" --strictPort >/dev/null 2>&1 &
server=$!
trap 'kill "${server}" 2>/dev/null || true; rm -rf -- "${work:?}"' EXIT
for _ in $(seq 1 30); do curl -sf "http://localhost:${port}/feed-exploration-experiment/" >/dev/null && break; sleep 0.5; done
mkdir -p "${repo_root}/docs/img"
"${chrome}" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1.5 \
  --virtual-time-budget=8000 --blink-settings=preferredColorScheme=1 --user-data-dir="${work}/profile" \
  --window-size=1280,712 --screenshot="${repo_root}/docs/img/dashboard-page1.png" \
  "http://localhost:${port}/feed-exploration-experiment/#/" 2>/dev/null
echo "wrote docs/img/dashboard-page1.png ($(du -h "${repo_root}/docs/img/dashboard-page1.png" | cut -f1))"
