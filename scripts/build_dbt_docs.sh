#!/usr/bin/env bash
# Regenerate the dbt docs site served at <Pages>/dbt/ (exports/dbt/index.html), as a snapshot.
# Runs `dbt docs generate --static` against prod: it compiles the project and reads table metadata
# (INFORMATION_SCHEMA), never table data. Reports the bytes those metadata queries billed, replaces
# local paths with repo-relative ones, and refuses to copy the file if it finds credentials, email
# addresses or local paths.
# Usage: scripts/build_dbt_docs.sh   (needs .env, dbt/profiles.yml and gcloud auth, like scripts/dbt.sh)
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; source "${repo_root}/.env"; set +a
start="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
"${repo_root}/scripts/dbt.sh" docs generate --static --target prod >/dev/null
html="${repo_root}/dbt/target/static_index.html"

# Bytes billed by this run's queries (catalog reads), from the project's job history.
sleep 5
bq query --nouse_legacy_sql --maximum_bytes_billed=1000000000 --format=csv "
select count(*) as jobs, coalesce(sum(total_bytes_billed), 0) as bytes_billed
from \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
where creation_time >= timestamp('${start}') and job_type = 'QUERY'" 2>/dev/null | tail -1 \
  | awk -F, '{printf "docs generate: %s query jobs, %.3f GB billed\n", $1, $2 / 1e9}'

python3 - "${html}" "${repo_root}" <<'PY'
import re, sys
path, root = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
text = text.replace(root + "/", "").replace(root, ".")
home = re.escape(str(__import__("pathlib").Path.home()))
patterns = {
    "local path": rf"{home}|/Users/[A-Za-z0-9._-]+|[A-Z]:\\\\Users",
    "email": r"[A-Za-z0-9._%+-]+@(?!example\.com)[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "credential": r"private_key|BEGIN [A-Z ]*PRIVATE KEY|client_secret|refresh_token|access_token|password\"\s*:",
}
found = {k: sorted(set(re.findall(p, text)))[:5] for k, p in patterns.items()}
found = {k: v for k, v in found.items() if v}
if found:
    sys.exit(f"refusing to publish: {found}")
open(path, "w", encoding="utf-8").write(text)
print("scan: no credentials, emails or local paths")
PY
mkdir -p "${repo_root}/exports/dbt"
cp "${html}" "${repo_root}/exports/dbt/index.html"
echo "wrote exports/dbt/index.html ($(du -h "${repo_root}/exports/dbt/index.html" | cut -f1)), generated ${start}"
