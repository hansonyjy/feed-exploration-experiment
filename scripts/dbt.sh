#!/usr/bin/env bash
# Run dbt for this repo: loads .env (GCP_PROJECT), uses the pinned uv environment, and points dbt at
# dbt/ for both the project and profiles.yml. Example: scripts/dbt.sh build --select staging
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${repo_root}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${repo_root}/.env"
  set +a
fi
: "${GCP_PROJECT:?set GCP_PROJECT in .env}"
cd "${repo_root}"
exec uv run dbt "$@" --project-dir "${repo_root}/dbt" --profiles-dir "${repo_root}/dbt"
