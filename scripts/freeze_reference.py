"""Freeze the full-data D26 bucket edges and D25/D29 thresholds as committed dbt seeds (D55).

Reads the prod tables staging.int_duration_buckets_computed and staging.int_reference_thresholds_computed
and writes dbt/seeds/frozen_duration_buckets.csv and dbt/seeds/frozen_reference_thresholds.csv.
Runs once, after the prod build of those two models: it refuses to overwrite a seed that already holds
values. Reads two 10-row tables (well under 1 GB; capped by maximum_bytes_billed).
Usage: uv run python scripts/freeze_reference.py
"""

import csv
import os
import sys
from pathlib import Path

from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parents[1]
SEEDS = REPO_ROOT / "dbt" / "seeds"
MAX_BYTES = 1_000_000_000

FREEZES = {
    "frozen_duration_buckets": (
        "int_duration_buckets_computed",
        ["duration_bucket", "lower_exclusive_ms", "upper_inclusive_ms", "n_reference_rows"],
    ),
    "frozen_reference_thresholds": (
        "int_reference_thresholds_computed",
        ["duration_bucket", "median_play_time_ms", "n_reference_rows"],
    ),
}


def load_env() -> str:
    env = REPO_ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"'))
    return os.environ["GCP_PROJECT"]


def fetch(client: bigquery.Client, project: str, table: str, columns: list[str]) -> list[dict]:
    sql = f"select {', '.join(columns)} from `{project}.staging.{table}` order by duration_bucket"
    job = client.query(sql, job_config=bigquery.QueryJobConfig(maximum_bytes_billed=MAX_BYTES))
    return [dict(row) for row in job.result()]


def check(name: str, rows: list[dict]) -> None:
    buckets = [r["duration_bucket"] for r in rows]
    if buckets != list(range(1, 11)):
        sys.exit(f"{name}: expected buckets 1-10, got {buckets}")
    if name == "frozen_duration_buckets":
        uppers = [r["upper_inclusive_ms"] for r in rows[:9]]
        if None in uppers or uppers != sorted(set(uppers)):
            sys.exit(f"{name}: upper edges must be distinct and increasing, got {uppers}")
        if rows[0]["lower_exclusive_ms"] is not None or rows[9]["upper_inclusive_ms"] is not None:
            sys.exit(f"{name}: buckets 1 and 10 must be open-ended")
        if any(rows[i]["lower_exclusive_ms"] != rows[i - 1]["upper_inclusive_ms"] for i in range(1, 10)):
            sys.exit(f"{name}: each lower edge must equal the previous upper edge")
    else:
        if any(r["median_play_time_ms"] is None or r["median_play_time_ms"] < 0 for r in rows):
            sys.exit(f"{name}: medians must be non-null and non-negative")


def main() -> None:
    project = load_env()
    client = bigquery.Client(project=project, location="US")
    for seed, (table, columns) in FREEZES.items():
        path = SEEDS / f"{seed}.csv"
        if path.exists() and len(path.read_text().strip().splitlines()) > 1:
            sys.exit(f"{path} already holds frozen values; refusing to overwrite (D55)")
        rows = fetch(client, project, table, columns)
        check(seed, rows)
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            for r in rows:
                writer.writerow({c: "" if r[c] is None else r[c] for c in columns})
        print(f"wrote {path.relative_to(REPO_ROOT)} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
