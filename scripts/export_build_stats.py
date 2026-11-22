"""Export build statistics for the dashboard's "How this was built" section (D61). No outcomes.

Writes two small committed files, so the dashboard never needs the gitignored dbt target or live BigQuery:
  exports/build/dbt_nodes.csv           one row per dbt model, test and seed in dbt/target/manifest.json
                                        (name, resource type, layer); run after `scripts/dbt.sh parse`
  exports/build/bytes_billed_by_month.csv  query jobs and bytes billed per Pacific month, from
                                        INFORMATION_SCHEMA.JOBS_BY_PROJECT (the same source as
                                        scripts/bytes_billed.sh); a snapshot as of the export date

Usage: uv run python scripts/export_build_stats.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date
from pathlib import Path

from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "exports" / "build"
sys.path.insert(0, str(REPO_ROOT / "analysis"))
from comparison_a import load_env  # noqa: E402

BYTES_SQL = """
select
  format_timestamp('%Y-%m', creation_time, 'America/Los_Angeles') as month_pt,
  count(*) as n_query_jobs,
  sum(total_bytes_billed) as bytes_billed
from `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
where job_type = 'QUERY'
group by month_pt
order by month_pt
"""


def dbt_nodes() -> list[dict]:
    manifest = json.loads((REPO_ROOT / "dbt" / "target" / "manifest.json").read_text())
    rows = []
    for node in manifest["nodes"].values():
        kind = node["resource_type"]
        if kind not in ("model", "test", "seed"):
            continue
        layer = node["fqn"][1] if kind == "model" and len(node["fqn"]) > 2 else ""
        rows.append({"name": node["name"], "resource_type": kind, "layer": layer})
    return sorted(rows, key=lambda r: (r["resource_type"], r["layer"], r["name"]))


def bytes_by_month() -> list[dict]:
    load_env()
    client = bigquery.Client(project=os.environ["GCP_PROJECT"], location=os.environ.get("GCP_LOCATION", "US"))
    job = client.query(BYTES_SQL, job_config=bigquery.QueryJobConfig(maximum_bytes_billed=10**9))
    snapshot = date.today().isoformat()
    return [{"month_pt": r.month_pt, "n_query_jobs": r.n_query_jobs, "bytes_billed": r.bytes_billed,
             "snapshot_date": snapshot} for r in job.result()]


def write(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path.relative_to(REPO_ROOT)} ({len(rows)} rows)")


def main() -> None:
    write("dbt_nodes.csv", dbt_nodes())
    write("bytes_billed_by_month.csv", bytes_by_month())


if __name__ == "__main__":
    main()
