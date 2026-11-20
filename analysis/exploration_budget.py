"""Exploration budget per segment (analysis_plan.md "Exploration budget"; D48, D54, D57, D59).

Guardrail limit: no binding guardrail worsens by more than 2% relative at the feed level. Binding
guardrails: hate and fast skip (D57); session exit is not identifiable and is left out (D53, D54).
For each segment and guardrail, the feed-level change at exploration share s (share of tab-1 exposures
that are random) is s x A / baseline, where A is the segment's Comparison A estimate (main run) and the
baseline is the D48 recommended rate (user segments: within the segment; item segments: overall; D59).
s is interpolated only between 0.658% and 1.388%; nothing is extrapolated.

Reported per segment: the recommended share (the largest s in range that keeps every binding guardrail at
or below 2% at the point estimate, or "at least 1.388%", or "below 0.658%"), the binding guardrail, the
feed-level change of each guardrail at both ends of the range with intervals, a flag when a guardrail's
interval crosses 2% in the range, and the expected cost and benefit per 1,000 tab-1 impressions at the
recommended share. The overall row uses the overall Comparison A results.

Usage:
  uv run python analysis/exploration_budget.py --synthetic     # code check; reads nothing
  uv run python analysis/exploration_budget.py --target prod [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd
from google.cloud import bigquery

from comparison_a import DATASETS, REPO_ROOT, load_env, read
from segments import ITEM_DIMS, MAP_PATH, USER_DIMS, require_committed_map

LIMIT = 0.02
S_LOW, S_HIGH = 0.00658, 0.01388
GUARDRAILS = ["hate", "fast_skip"]
COST, BENEFITS = "effective_view", ["new_author_follow", "new_category_effective_view"]


def baseline_query(project: str, staging: str, marts: str) -> str:
    return f"""
        with rec_days as (
            select
                user_id,
                event_date,
                safe_divide(sum(sum_hate), sum(n_hate)) as hate,
                safe_divide(sum(sum_fast_skip), sum(n_fast_skip)) as fast_skip
            from `{project}.{marts}.mart_user_day_arm_metrics`
            where is_rand = 0 and has_valid_duration
            group by user_id, event_date
        )
        select r.user_id, avg(r.hate) as hate, avg(r.fast_skip) as fast_skip,
            any_value(p.activity_tercile) as activity_tercile, any_value(p.active_group) as active_group,
            any_value(p.tenure_band) as tenure_band, any_value(p.follow_band) as follow_band
        from rec_days as r
        left join `{project}.{staging}.int_user_pre_profile` as p on r.user_id = p.user_id
        group by r.user_id
    """


def baselines(users: pd.DataFrame, merge_map: pd.DataFrame) -> pd.DataFrame:
    """D48 baseline per (dimension, segment): mean over users of each user's mean daily rec rate."""
    rows = [dict(dimension="overall", segment="all", **users[GUARDRAILS].mean().to_dict())]
    for dim in USER_DIMS:
        m = merge_map[merge_map["dimension"] == dim].set_index("segment")["final_segment"]
        seg = users[dim].astype("string").map(m)
        for name, g in users.assign(seg=seg).dropna(subset=["seg"]).groupby("seg"):
            rows.append(dict(dimension=dim, segment=name, **g[GUARDRAILS].mean().to_dict()))
    out = pd.DataFrame(rows)
    overall = out.iloc[0]
    for dim in ITEM_DIMS:
        segs = merge_map.loc[merge_map["dimension"] == dim, "final_segment"].unique()
        out = pd.concat([out, pd.DataFrame([dict(dimension=dim, segment=s, hate=overall["hate"],
                                                 fast_skip=overall["fast_skip"]) for s in segs])])
    return out.reset_index(drop=True)


def budget(effects: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    """effects: one row per (dimension, segment, metric) with estimate, ci_low, ci_high."""
    wide = effects.pivot_table(index=["dimension", "segment"], columns="metric",
                               values=["estimate", "ci_low", "ci_high"])
    rows = []
    for (dim, seg), r in wide.iterrows():
        b = base[(base["dimension"] == dim) & (base["segment"] == seg)]
        if b.empty:
            continue
        row = dict(dimension=dim, segment=seg)
        caps = {}
        for g in GUARDRAILS:
            bl = float(b.iloc[0][g])
            rel, lo, hi = (r[(k, g)] / bl for k in ("estimate", "ci_low", "ci_high"))
            caps[g] = LIMIT / rel if rel > 0 else np.inf
            row.update({f"{g}_baseline": bl, f"{g}_rel_effect": rel, f"{g}_rel_low": lo, f"{g}_rel_high": hi,
                        f"{g}_feed_change_at_low": S_LOW * rel, f"{g}_feed_change_at_high": S_HIGH * rel,
                        f"{g}_feed_change_at_high_ci_low": S_HIGH * lo, f"{g}_feed_change_at_high_ci_high": S_HIGH * hi,
                        f"{g}_interval_crosses_limit": bool(S_LOW * lo <= LIMIT <= S_HIGH * hi)})
        cap = min(caps.values())
        binding = min(caps, key=caps.get)
        if cap >= S_HIGH:
            share, label, binding = S_HIGH, "at least 1.388% (top of the observed range)", "none in range"
        elif cap < S_LOW:
            share, label = np.nan, "below 0.658% (binds below the observed range)"
        else:
            share, label = cap, f"{100 * cap:.3f}%"
        row.update(recommended_share=share, recommended_share_label=label, binding_guardrail=binding,
                   any_interval_crosses_limit=any(row[f"{g}_interval_crosses_limit"] for g in GUARDRAILS))
        for m in [COST, *BENEFITS]:
            row[f"{m}_change_per_1000_impressions"] = share * r[("estimate", m)] * 1000 if share == share else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def synthetic() -> tuple[pd.DataFrame, pd.DataFrame]:
    effects = pd.DataFrame([
        # segment that binds inside the range on fast skip, one that never binds, one below the range
        *[dict(dimension="activity_tercile", segment="1", metric=m, estimate=e, ci_low=e * 0.9, ci_high=e * 1.1)
          for m, e in [("hate", 0.0005), ("fast_skip", 0.60), ("effective_view", -0.35),
                       ("new_author_follow", -0.0015), ("new_category_effective_view", -0.005)]],
        *[dict(dimension="activity_tercile", segment="2", metric=m, estimate=e, ci_low=e * 0.9, ci_high=e * 1.1)
          for m, e in [("hate", 0.0002), ("fast_skip", 0.20), ("effective_view", -0.30),
                       ("new_author_follow", -0.0015), ("new_category_effective_view", -0.005)]],
        *[dict(dimension="activity_tercile", segment="3", metric=m, estimate=e, ci_low=e * 0.5, ci_high=e * 1.5)
          for m, e in [("hate", 0.0030), ("fast_skip", 0.30), ("effective_view", -0.30),
                       ("new_author_follow", -0.0015), ("new_category_effective_view", -0.005)]],
    ])
    base = pd.DataFrame([dict(dimension="activity_tercile", segment=s, hate=0.0005, fast_skip=0.33) for s in "123"])
    return effects, base


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=list(DATASETS), default="prod")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    if args.synthetic:
        effects, base = synthetic()
        out = budget(effects, base)
        print(out[["segment", "fast_skip_rel_effect", "hate_rel_effect", "recommended_share_label",
                   "binding_guardrail", "any_interval_crosses_limit"]].to_string(index=False))
        print("expected: 1 binds on fast skip at 1.100%; 2 at least 1.388%; 3 binds on hate below 0.658%, flagged")
        return
    if args.target == "dev":
        sys.exit("the budget reads segment outcomes, which run on prod only (D57); use --synthetic")
    require_committed_map()
    load_env()
    project = os.environ["GCP_PROJECT"]
    client = bigquery.Client(project=project, location=os.environ.get("GCP_LOCATION", "US"))
    staging, marts = DATASETS[args.target]
    sql = baseline_query(project, staging, marts)
    b = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)).total_bytes_processed
    print(f"read estimated {b / 1e9:.3f} GB")
    if args.dry_run:
        return
    merge_map = pd.read_csv(MAP_PATH, dtype=str)
    base = baselines(read(client, sql), merge_map)
    seg = pd.read_csv(REPO_ROOT / "exports/segments_prod.csv", dtype={"segment": str})
    a = pd.read_csv(REPO_ROOT / "exports/comparison_a_prod.csv")
    a = a[(a["analysis"] == "A_request") & (a["variant"] == "main") & (a["weighting"] == "equal_user")]
    overall = a.assign(dimension="overall", segment="all")[["dimension", "segment", "metric", "estimate",
                                                             "ci_low", "ci_high"]]
    effects = pd.concat([overall, seg[["dimension", "segment", "metric", "estimate", "ci_low", "ci_high"]]])
    out = budget(effects, base)
    path = REPO_ROOT / "exports/exploration_budget_prod.csv"
    out.to_csv(path, index=False)
    print(f"wrote {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
