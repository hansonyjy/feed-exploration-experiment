"""Minimum-detectable-effect merge of segments (analysis_plan.md; D39, D40, D58). No outcomes are read.

Inputs: pre-period placebo sums per user (int_segment_power_inputs), pre-period user segments
(int_user_pre_profile), the random item's segments (int_random_item_segments), and the count of main-run
random requests per user (requests whose random item and at least one recommended item have a valid
duration; mart_random_request_items read for keys and flags only).

For each dimension, a segment's MDE for the equal-user Comparison A estimate is
(1.96 + 0.84) * sqrt(sum_u sigma^2 * (rho + (1 - rho) / m_u)) / N. A segment with MDE > 1 pp merges with
its smaller adjacent segment (categories: with the smallest other segment); repeat until all pass.

Usage:
  uv run python scripts/make_segment_merges.py --target dev    # code check; analysis/output_dev/
  uv run python scripts/make_segment_merges.py --target prod   # writes dbt/seeds/segment_merge_map.csv
The prod map is committed on its own before any segment outcome is read (D57), and is never overwritten.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "analysis"))
from comparison_a import DATASETS, load_env, read  # noqa: E402

Z = 1.959964 + 0.841621
MDE_LIMIT = 0.01
SEED_PATH = REPO_ROOT / "dbt/seeds/segment_merge_map.csv"

USER_DIMS = ["activity_tercile", "active_group", "tenure_band", "follow_band"]
ITEM_DIMS = ["duration_bucket", "category_segment"]
ACTIVE_ORDER = ["new_or_low", "middle_active", "full_active", "high_active"]
ACTIVITY_ORDER = ["no_pre_period", "1", "2", "3"]


def queries(project: str, staging: str, marts: str) -> dict[str, str]:
    return {
        "power": ("select user_id, n_placebo_requests, sum_d, sum_d2 "
                  f"from `{project}.{staging}.int_segment_power_inputs`"),
        "profile": ("select user_id, activity_tercile, active_group, tenure_band, follow_band "
                    f"from `{project}.{staging}.int_user_pre_profile`"),
        "bands": f"select dimension, band_order, merged_band from `{project}.{staging}.segment_band_map`",
        "requests": f"""
            with main_run as (
                select request_key, any_value(user_id) as user_id
                from `{project}.{marts}.mart_random_request_items`
                group by request_key
                having logical_or(is_rand = 1 and has_valid_duration)
                    and logical_or(is_rand = 0 and has_valid_duration)
            )
            select m.user_id, cast(s.duration_bucket as string) as duration_bucket, s.category_segment
            from main_run as m
            inner join `{project}.{staging}.int_random_item_segments` as s on m.request_key = s.request_key
        """,
    }


def variance_inputs(power: pd.DataFrame) -> tuple[float, float]:
    """sigma^2 of the placebo difference and its one-way ANOVA intraclass correlation by user."""
    p = power[power["n_placebo_requests"] > 0]
    n = p["n_placebo_requests"].to_numpy(float)
    s = p["sum_d"].to_numpy(float)
    s2 = p["sum_d2"].to_numpy(float)
    big_n, k = n.sum(), len(n)
    sst = s2.sum() - s.sum() ** 2 / big_n
    ssb = (s ** 2 / n).sum() - s.sum() ** 2 / big_n
    ssw = sst - ssb
    msb, msw = ssb / (k - 1), ssw / (big_n - k)
    n0 = (big_n - (n ** 2).sum() / big_n) / (k - 1)
    rho = max(0.0, (msb - msw) / (msb + (n0 - 1) * msw))
    return sst / (big_n - 1), rho


def mde(m_u: np.ndarray, sigma2: float, rho: float) -> float:
    m_u = m_u[m_u > 0]
    return Z * np.sqrt((sigma2 * (rho + (1 - rho) / m_u)).sum()) / len(m_u)


def natural_order(dim: str, labels: list[str], bands: pd.DataFrame) -> list[str]:
    if dim == "activity_tercile":
        return [x for x in ACTIVITY_ORDER if x in labels]
    if dim == "active_group":
        return [x for x in ACTIVE_ORDER if x in labels]
    if dim in ("tenure_band", "follow_band"):
        name = "register_days_range" if dim == "tenure_band" else "follow_user_num_range"
        order = (bands[bands["dimension"] == name].groupby("merged_band")["band_order"].min()
                 .sort_values().index.tolist())
        return [x for x in order if x in labels]
    if dim == "duration_bucket":
        return sorted(labels, key=int)
    return sorted(labels)  # categories: order unused (they merge with the smallest segment)


def merge_dimension(dim: str, unit: pd.DataFrame, power: pd.DataFrame, order: list[str],
                    overall: tuple[float, float]) -> pd.DataFrame:
    """unit: one row per main-run random request with user_id and the dimension's label."""
    groups = {label: [label] for label in order}  # final segment -> member labels, kept in order

    def stats(members: list[str]) -> dict:
        rows = unit[unit[dim].isin(members)]
        m_u = rows.groupby("user_id").size().to_numpy(float)
        sub = power[power["user_id"].isin(rows["user_id"].unique()) & (power["n_placebo_requests"] > 0)]
        if dim in USER_DIMS and sub["user_id"].nunique() > 1:
            sigma2, rho = variance_inputs(sub)
        else:
            # Item segments, and user segments without pre-period requests (no_pre_period): overall inputs.
            sigma2, rho = overall
        return dict(n_users=len(m_u), n_random_requests=int(m_u.sum()), sigma2=sigma2, rho=rho,
                    mde=mde(m_u, sigma2, rho))

    while True:
        current = {name: stats(members) for name, members in groups.items()}
        failing = [n for n, st in current.items() if st["mde"] > MDE_LIMIT]
        if any(np.isnan(st["mde"]) for st in current.values()):
            sys.exit(f"{dim}: an MDE could not be computed")
        if not failing or len(groups) == 1:
            break
        worst = max(failing, key=lambda n: current[n]["mde"])
        names = list(groups)
        if dim == "category_segment":
            others = [n for n in names if n != worst]
            partner = min(others, key=lambda n: current[n]["n_random_requests"])
        else:
            i = names.index(worst)
            neighbours = [names[j] for j in (i - 1, i + 1) if 0 <= j < len(names)]
            partner = min(neighbours, key=lambda n: current[n]["n_random_requests"])
        a, b = sorted([worst, partner], key=names.index)
        merged = groups[a] + groups[b]
        new_name = "+".join(merged)
        groups = {(new_name if n == a else n): (merged if n == a else g)
                  for n, g in groups.items() if n != b}

    rows = []
    for name, members in groups.items():
        st = current[name]
        for label in members:
            rows.append(dict(dimension=dim, segment=label, final_segment=name,
                             segment_order=order.index(label) + 1, n_users=st["n_users"],
                             n_random_requests=st["n_random_requests"], sigma2=round(st["sigma2"], 6),
                             rho=round(st["rho"], 6), mde_pp=round(100 * st["mde"], 4)))
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=list(DATASETS), default="dev")
    args = parser.parse_args()
    if args.target == "prod" and SEED_PATH.exists() and len(SEED_PATH.read_text().splitlines()) > 1:
        sys.exit(f"{SEED_PATH} already holds a merge map; refusing to overwrite (D57)")
    load_env()
    project = os.environ["GCP_PROJECT"]
    client = bigquery.Client(project=project, location=os.environ.get("GCP_LOCATION", "US"))
    staging, marts = DATASETS[args.target]
    qs = queries(project, staging, marts)
    total = sum(client.query(q, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
                .total_bytes_processed for q in qs.values())
    print(f"reads estimated {total / 1e9:.3f} GB")
    power, profile, bands, requests = (read(client, qs[k]) for k in ("power", "profile", "bands", "requests"))

    requests = requests.merge(profile, on="user_id", how="left")
    overall = variance_inputs(power)
    print(f"overall placebo sigma^2 = {overall[0]:.4f}, rho = {overall[1]:.4f}; "
          f"{len(requests):,} main-run random requests, {requests.user_id.nunique():,} users")
    out = []
    for dim in USER_DIMS + ITEM_DIMS:
        unit = requests[["user_id", dim]].dropna()
        unit = unit[unit[dim] != "unknown"]
        order = natural_order(dim, sorted(unit[dim].unique()), bands)
        out.append(merge_dimension(dim, unit, power, order, overall))
    result = pd.concat(out, ignore_index=True)
    path = SEED_PATH if args.target == "prod" else REPO_ROOT / "analysis/output_dev/segment_merge_map_dev.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(path, index=False, lineterminator="\n")
    print(result.to_string(index=False))
    print(f"wrote {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
