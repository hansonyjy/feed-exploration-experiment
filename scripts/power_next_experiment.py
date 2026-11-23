"""Sample size for the next experiment in docs/memo.md (user-level randomization, four arms), in two tiers.

All variances come from Comparison A's data (marts.mart_random_request_items, Apr 23 to May 8), with each
user as the unit (the cluster), equal weight per user. The window is about 16 days; a 4-week test gives each
user more impressions and slots, so these between-user variances are conservative.

Tier 1, slot level (what targeting saves): compare targeted slots with random slots directly, as in this
analysis. Outcome: a user's effective-view rate on exploration slots. Its spread across users is measured
on random slots with a valid duration. Target difference: 5 pp.

Tier 2, feed level (how far the share can go, and the guardrails): outcome: a user's effective-view rate per
impression, measured on recommended items with a valid duration (the main run, D23). Target: 0.2 pp. At that
sample, also the minimum detectable change in a user's hate rate (all recommended rows), compared with
hate's guardrail limit (2% of the feed's hate rate), and the users hate would need to detect that limit.

Both tiers: two-sided, 80% power, alpha 0.05 split over the three planned comparisons (Bonferroni):
    n per arm = 2 * (z_{1 - alpha / (2 * 3)} + z_{0.80})^2 * sigma^2 / delta^2

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

SLOT_DELTA = 0.05    # tier 1: 5 pp in a slot's effective-view rate
FEED_DELTA = 0.002   # tier 2: 0.2 pp in a user's effective-view rate per impression
HATE_LIMIT = 0.02    # guardrail: at most 2% relative worsening of the feed's hate rate
ALPHA = 0.05
COMPARISONS = 3      # random 2% vs control, targeted 2% vs random 2%, targeted 3% vs targeted 2%
POWER = 0.80
MAX_BYTES = 5 * 10**9


def sql(project: str) -> str:
    return f"""
        with users as (
            select
                user_id,
                avg(if(is_rand = 0 and has_valid_duration, cast(effective_view as float64), null)) as feed_ev,
                avg(if(is_rand = 0, cast(hate as float64), null)) as feed_hate,
                avg(if(is_rand = 1 and has_valid_duration, cast(effective_view as float64), null)) as slot_ev,
                countif(is_rand = 1 and has_valid_duration) as n_slots
            from `{project}.marts.mart_random_request_items`
            group by user_id
        )
        select
            count(feed_ev) as n_users_feed, avg(feed_ev) as feed_ev_mean, var_samp(feed_ev) as feed_ev_var,
            avg(feed_hate) as feed_hate_mean, var_samp(feed_hate) as feed_hate_var,
            count(slot_ev) as n_users_slot, avg(slot_ev) as slot_ev_mean, var_samp(slot_ev) as slot_ev_var,
            approx_quantiles(if(n_slots > 0, n_slots, null), 2)[offset(1)] as median_slots_per_user
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
    n_for = lambda var, delta: math.ceil(2 * z**2 * var / delta**2)
    slot_n = n_for(r.slot_ev_var, SLOT_DELTA)
    feed_n = n_for(r.feed_ev_var, FEED_DELTA)
    hate_limit_abs = HATE_LIMIT * r.feed_hate_mean
    hate_mde_at_feed_n = z * math.sqrt(2 * r.feed_hate_var / feed_n)
    hate_n = n_for(r.feed_hate_var, hate_limit_abs)
    row = {
        "alpha": ALPHA, "comparisons": COMPARISONS, "power": POWER,
        "slot_delta": SLOT_DELTA, "slot_n_users_measured": r.n_users_slot, "slot_ev_mean": r.slot_ev_mean,
        "slot_ev_sd": math.sqrt(r.slot_ev_var), "median_slots_per_user": r.median_slots_per_user,
        "slot_users_per_arm": slot_n,
        "feed_delta": FEED_DELTA, "feed_n_users_measured": r.n_users_feed, "feed_ev_mean": r.feed_ev_mean,
        "feed_ev_sd": math.sqrt(r.feed_ev_var), "feed_users_per_arm": feed_n, "feed_users_total_four_arms": 4 * feed_n,
        "hate_mean": r.feed_hate_mean, "hate_sd": math.sqrt(r.feed_hate_var), "hate_limit_abs": hate_limit_abs,
        "hate_mde_at_feed_n": hate_mde_at_feed_n, "hate_users_per_arm_for_limit": hate_n,
        "hate_needs_more_users": hate_n > feed_n,
    }
    out = REPO_ROOT / "exports" / "memo" / "power_next_experiment.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row), lineterminator="\n")
        w.writeheader()
        w.writerow(row)
    for k, v in row.items():
        print(f"{k}: {v}")
    print(f"wrote {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
