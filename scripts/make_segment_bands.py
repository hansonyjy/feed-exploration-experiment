"""Write dbt/seeds/segment_band_map.csv: the D46 merge of tenure and follow-count bands.

Rule (D46, mirroring D14): bands are ordered by their lower bound; while any group has fewer than
1,000 users, the smallest such group merges with its smaller adjacent neighbour (the earlier one on a
tie). Uses only user counts per band in raw.user_features (all 27,285 users), never outcome data.
Null or empty bands map to 'unknown' and are excluded from that dimension's segment tests.

Usage: uv run python scripts/make_segment_bands.py
"""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "dbt" / "seeds" / "segment_band_map.csv"
MIN_USERS = 1000
DIMENSIONS = ["register_days_range", "follow_user_num_range"]


def load_env() -> None:
    env = REPO_ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def lower_bound(band: str) -> float:
    match = re.search(r"\d+", band)
    return float(match.group()) if match else float("inf")


def merge(bands: list[tuple[str, int]]) -> dict[str, str]:
    """bands: [(band, n_users)] ordered. Returns band -> merged label."""
    groups = [[b] for b, _ in bands]
    counts = dict(bands)
    size = lambda g: sum(counts[b] for b in g)  # noqa: E731
    while len(groups) > 1:
        small = [i for i, g in enumerate(groups) if size(g) < MIN_USERS]
        if not small:
            break
        i = min(small, key=lambda j: (size(groups[j]), j))
        neighbours = [j for j in (i - 1, i + 1) if 0 <= j < len(groups)]
        j = min(neighbours, key=lambda k: (size(groups[k]), k))
        lo, hi = sorted((i, j))
        groups[lo:hi + 1] = [groups[lo] + groups[hi]]
    mapping = {}
    for g in groups:
        label = g[0] if len(g) == 1 else f"{g[0]} to {g[-1]}"
        for b in g:
            mapping[b] = label
    return mapping


def main() -> None:
    load_env()
    project = os.environ["GCP_PROJECT"]
    client = bigquery.Client(project=project, location=os.environ.get("GCP_LOCATION", "US"))
    rows = []
    for dim in DIMENSIONS:
        sql = (f"select {dim} as band, count(*) as n from `{project}.raw.user_features` "
               f"where {dim} is not null and {dim} != '' group by band")
        job = client.query(sql, job_config=bigquery.QueryJobConfig(maximum_bytes_billed=10**8))
        bands = sorted(((r.band, r.n) for r in job.result()), key=lambda x: lower_bound(x[0]))
        mapping = merge(bands)
        for order, (band, n) in enumerate(bands, start=1):
            rows.append({"dimension": dim, "band": band, "band_order": order, "n_users": n,
                         "merged_band": mapping[band]})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["dimension", "band", "band_order", "n_users", "merged_band"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT.relative_to(REPO_ROOT)}")
    for r in rows:
        print(f"  {r['dimension']:22s} {r['band']:>10s} {r['n_users']:>6,} -> {r['merged_band']}")


if __name__ == "__main__":
    main()
