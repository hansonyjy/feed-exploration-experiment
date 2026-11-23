"""Sample size for the next experiment in docs/memo.md (user-level randomization, four arms).

Outcome: a user's effective-view rate per impression over the test. Its spread across users comes from
Comparison A's data (marts.mart_random_request_items): each user's effective-view rate on recommended
items with a valid duration (the main run, D23), averaged per user, equal weight per user, Apr 23 to May 8.
That window is about 16 days; a 4-week test gives each user more impressions, so the between-user variance
measured here is conservative (it includes more within-user noise than a 4-week average would).

Users per arm to detect a difference of DELTA in the user-level rate between two arms, two-sided, at 80%
power and alpha 0.05 split over the three planned comparisons (Bonferroni):
    n = 2 * (z_{1 - alpha / (2 * 3)} + z_{0.80})^2 * sigma^2 / DELTA^2

Usage:
  uv run python scripts/power_next_experiment.py --dry-run   # bytes only
  uv run python scripts/power_next_experiment.py             # writes exports/memo/power_next_experiment.csv
Stops without running if the query would scan more than 5 GB.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys
from pathlib import Path
from statistics import NormalDist

from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "analysis"))
from comparison_a import load_env  # noqa: E402

DELTA = 0.01  # 1 pp in the user-level effective-view rate
ALPHA = 0.05
COMPARISONS = 3  # random 2% vs control, targeted 2% vs random 2%, targeted 3% vs targeted 2%
POWER = 0.80
MAX_BYTES = 5 * 10**9


def sql(project: str) -> str:
    return f"""
        with users as (
            select user_id, avg(cast(effective_view as float64)) as rate, count(*) as n_items
            from `{project}.marts.mart_random_request_items`
            where is_rand = 0 and has_valid_duration
            group by user_id
        )
        select count(*) as n_users, avg(rate) as mean_rate, var_samp(rate) as var_rate,
               approx_quantiles(n_items, 2)[offset(1)] as median_items_per_user
        from users
    """


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    load_env()
    project = os.environ["GCP_PROJECT"]
    client = bigquery.Client(project=project, location=os.environ.get("GCP_LOCATION", "US"))
    q = sql(project)
    est = client.query(q, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)).total_bytes_processed
    print(f"query estimated {est / 1e9:.3f} GB")
    if est > MAX_BYTES:
        print("over 5 GB: not run. Memo says: size it before launch with a power analysis on user-level variance.")
        return 1
    if args.dry_run:
        return 0
    job = client.query(q, job_config=bigquery.QueryJobConfig(maximum_bytes_billed=max(int(est * 1.25), 10**9)))
    r = list(job.result())[0]
    z = NormalDist().inv_cdf(1 - ALPHA / (2 * COMPARISONS)) + NormalDist().inv_cdf(POWER)
    n = math.ceil(2 * z**2 * r.var_rate / DELTA**2)
    out = REPO_ROOT / "exports" / "memo" / "power_next_experiment.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    row = {"n_users_measured": r.n_users, "mean_user_rate": r.mean_rate, "sd_user_rate": math.sqrt(r.var_rate),
           "median_items_per_user": r.median_items_per_user, "delta": DELTA, "alpha": ALPHA,
           "comparisons": COMPARISONS, "power": POWER, "users_per_arm": n, "users_total_four_arms": 4 * n}
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row), lineterminator="\n")
        w.writeheader()
        w.writerow(row)
    print(row)
    print(f"wrote {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
