"""Bridge Comparison B and C's targeting gap (D60, reporting only).

In random-minus-recommended terms, main run, for every metric:
  B on all pool exposures (equal weight per video)                     exports/comparison_b_<target>.csv
  B on C's sample: the same estimator on pool exposures from C's kept user-days (D57 same-day rule)
  C's targeting gap, sign flipped (users weighted equally, days by random items)
sample part = B on C's sample - B; weighting part = (-C targeting) - B on C's sample. They add up to
-C targeting - B. B on C's sample gets B's inference (video and user bootstraps, video fixed effects).

Usage: uv run python analysis/bridge_b_c.py --target prod [--dry-run]
Needs comparison_b and comparison_c outputs for the same target.
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd
from google.cloud import bigquery

from comparison_a import DATASETS, ITEM_METRICS, REPO_ROOT, agree, load_env, read
from comparison_b import run as run_b
from comparison_c import query as c_query
from comparison_c import user_day_rates


def b_query(project: str, marts: str) -> str:
    cols = ", ".join(["video_id", "user_id", "event_date", "is_rand", "has_valid_duration", "is_ad_pool_video",
                      "is_top_user_day", *ITEM_METRICS])
    return f"select {cols} from `{project}.{marts}.mart_same_video_items`"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=list(DATASETS), default="prod")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    load_env()
    project = os.environ["GCP_PROJECT"]
    client = bigquery.Client(project=project, location=os.environ.get("GCP_LOCATION", "US"))
    marts = DATASETS[args.target][1]
    qs = {"pool items": b_query(project, marts), "C cells": c_query(project, marts)}
    for name, q in qs.items():
        b = client.query(q, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)).total_bytes_processed
        print(f"read {name} estimated {b / 1e9:.3f} GB")
    if args.dry_run:
        return
    items, cells = read(client, qs["pool items"]), read(client, qs["C cells"])
    for m in ITEM_METRICS:
        items[m] = items[m].astype(float)
        cells[f"sum_{m}"], cells[f"n_{m}"] = cells[f"sum_{m}"].astype(float), cells[f"n_{m}"].astype(float)
    items["is_rand"] = items["is_rand"].astype(int)
    for c in ("has_valid_duration", "is_ad_pool_video", "is_top_user_day"):
        items[c] = items[c].astype(bool)
        cells[c] = cells[c].astype(bool)
    key = items["user_id"].astype(str) + "|" + items["event_date"].astype(str)

    out_dir = REPO_ROOT / ("exports" if args.target == "prod" else "analysis/output_dev")
    b_all = pd.read_csv(out_dir / f"comparison_b_{args.target}.csv")
    b_all = b_all[b_all["variant"] == "main"].set_index("metric")["estimate"]
    c = pd.read_csv(out_dir / f"comparison_c_{args.target}.csv")
    c_targ = c[(c["variant"] == "main") & (c["term"] == "targeting")].set_index("metric")["estimate"]

    rows = []
    for m in ITEM_METRICS:
        ud, kept_share = user_day_rates(cells, m, "main")
        kept = set(ud["user_id"].astype(str) + "|" + ud["event_date"].astype(str))
        r = run_b(items[key.isin(kept)], m, "main")
        r["bootstrap_and_regression_agree"] = agree(pd.Series(r))
        b_c = r["estimate"]
        rows.append(dict(metric=m, b_all=b_all[m], b_on_c_sample=b_c, b_on_c_sample_ci_low=r["ci_low"],
                         b_on_c_sample_ci_high=r["ci_high"], b_on_c_sample_ci_low_user=r["ci_low_user"],
                         b_on_c_sample_ci_high_user=r["ci_high_user"], b_on_c_sample_reg_p=r["reg_p"],
                         b_on_c_sample_agree=r["bootstrap_and_regression_agree"], b_on_c_sample_n_videos=r["n_videos"],
                         b_on_c_sample_n_items=r["n_items"], c_targeting_rand_minus_rec=-c_targ[m],
                         sample_part=b_c - b_all[m], weighting_part=-c_targ[m] - b_c,
                         share_random_items_kept=kept_share))
        print(f"  done {m}")
    path = out_dir / f"bridge_b_c_{args.target}.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"wrote {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
