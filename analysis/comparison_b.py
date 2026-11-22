"""Comparison B: the same pool video, recommended vs shown at random, tab 1 (analysis_plan.md, D43).

Pool videos (the 7,583 candidates) with at least one exposure in each arm, 2022-04-23 to 05-08. Per video,
the mean of random exposures minus the mean of recommended exposures; equal weight per video. Content is
held fixed, so the gap is the value of targeting.

Inference: bootstrap clustered by video (2,000 resamples, seed 20261115, 95% percentile intervals), with
a user-clustered bootstrap as robustness. Cross-check: OLS with video fixed effects, weights giving each
arm of each video a total of 0.5 (so the coefficient is the equal-video mean difference), SEs clustered by
video. Sensitivity runs as in A: excluding the top 0.1% of user-days, excluding AD pool videos, and
including missing-duration rows (non-duration metrics).

Usage:
  uv run python analysis/comparison_b.py --target dev [--dry-run]
Prod output goes to exports/comparison_b_prod.csv; dev output to analysis/output_dev/.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd
import pyfixest as pf
from google.cloud import bigquery
from scipy import sparse

from comparison_a import (ALPHA, DATASETS, ITEM_METRICS, N_BOOT, NON_DURATION_METRICS, REPO_ROOT, SEED,
                          agree, load_env, read)


def query(project: str, marts: str) -> str:
    cols = ", ".join(["video_id", "user_id", "is_rand", "has_valid_duration", "is_ad_pool_video",
                      "is_top_user_day", *ITEM_METRICS])
    return f"select {cols} from `{project}.{marts}.mart_same_video_items`"


def frame(items: pd.DataFrame, variant: str, metric: str) -> pd.DataFrame:
    df = items
    if variant == "top_user_day_excluded":
        df = df[~df["is_top_user_day"]]
    elif variant == "ad_pool_excluded":
        df = df[~df["is_ad_pool_video"]]
    if variant != "incl_missing_duration":
        df = df[df["has_valid_duration"]]
    df = df[df[metric].notna()]
    both = df.groupby("video_id")["is_rand"].nunique()
    return df[df["video_id"].isin(both[both == 2].index)]


def video_diffs(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    m = df.groupby(["video_id", "is_rand"])[metric].mean().unstack()
    return pd.DataFrame({"rec": m[0], "rand": m[1], "diff": m[1] - m[0]})


def boot_video(diffs: np.ndarray) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(diffs), size=(N_BOOT, len(diffs)))
    lo, hi = np.percentile(diffs[idx].mean(axis=1), [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    return lo, hi


def boot_user(df: pd.DataFrame, metric: str) -> tuple[float, float]:
    """Resample users; recompute each video's arm means from the drawn users' items."""
    users, u_idx = np.unique(df["user_id"].to_numpy(), return_inverse=True)
    videos, v_idx = np.unique(df["video_id"].to_numpy(), return_inverse=True)
    col = v_idx * 2 + df["is_rand"].to_numpy()
    shape = (len(users), 2 * len(videos))
    s = sparse.csr_matrix((df[metric].to_numpy(float), (u_idx, col)), shape=shape)
    n = sparse.csr_matrix((np.ones(len(df)), (u_idx, col)), shape=shape)
    rng = np.random.default_rng(SEED)
    draws = []
    for start in range(0, N_BOOT, 250):
        k = min(250, N_BOOT - start)
        w = np.stack([np.bincount(rng.integers(0, len(users), len(users)), minlength=len(users))
                      for _ in range(k)]).astype(float)
        sums = np.asarray((s.T @ w.T).T)
        cnts = np.asarray((n.T @ w.T).T)
        sums, cnts = sums.reshape(k, -1, 2), cnts.reshape(k, -1, 2)
        with np.errstate(invalid="ignore", divide="ignore"):
            means = sums / cnts
        diff = means[:, :, 1] - means[:, :, 0]
        draws.append(np.nanmean(diff, axis=1))
    lo, hi = np.percentile(np.concatenate(draws), [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    return lo, hi


def regress(df: pd.DataFrame, metric: str) -> tuple[float, float, float]:
    w = 0.5 / df.groupby(["video_id", "is_rand"])[metric].transform("count")
    fit = pf.feols(f"{metric} ~ is_rand | video_id", data=df.assign(w=w), weights="w",
                   vcov={"CRV1": "video_id"})
    return float(fit.coef()["is_rand"]), float(fit.se()["is_rand"]), float(fit.pvalue()["is_rand"])


def run(items: pd.DataFrame, metric: str, variant: str) -> dict:
    df = frame(items, variant, metric)
    d = video_diffs(df, metric)
    lo, hi = boot_video(d["diff"].to_numpy())
    ulo, uhi = boot_user(df, metric)
    coef, se, p = regress(df, metric)
    est, base = d["diff"].mean(), d["rec"].mean()
    return dict(analysis="B_same_video", metric=metric, variant=variant, weighting="equal_video",
                estimate=est, ci_low=lo, ci_high=hi, ci_low_user=ulo, ci_high_user=uhi, baseline_rec=base,
                relative=est / base if base else np.nan, n_videos=len(d), n_users=df["user_id"].nunique(),
                n_items=len(df), n_items_rand=int(df["is_rand"].sum()), reg_coef=coef, reg_se=se, reg_p=p)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=list(DATASETS), default="dev")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    load_env()
    project = os.environ["GCP_PROJECT"]
    client = bigquery.Client(project=project, location=os.environ.get("GCP_LOCATION", "US"))
    sql = query(project, DATASETS[args.target][1])
    b = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)).total_bytes_processed
    print(f"read estimated {b / 1e9:.3f} GB")
    if args.dry_run:
        return
    items = read(client, sql)
    for m in ITEM_METRICS:
        items[m] = items[m].astype(float)
    items["is_rand"] = items["is_rand"].astype(int)
    for c in ("has_valid_duration", "is_ad_pool_video", "is_top_user_day"):
        items[c] = items[c].astype(bool)
    print(f"loaded {len(items):,} pool-video items")

    rows = []
    for m in ITEM_METRICS:
        variants = ["main", "top_user_day_excluded", "ad_pool_excluded"]
        if m in NON_DURATION_METRICS:
            variants.append("incl_missing_duration")
        rows += [run(items, m, v) for v in variants]
        print(f"  done {m}")
    out = pd.DataFrame(rows)
    out["bootstrap_and_regression_agree"] = out.apply(agree, axis=1)
    out["user_bootstrap_significant"] = (out["ci_low_user"] > 0) | (out["ci_high_user"] < 0)
    out_dir = REPO_ROOT / ("exports" if args.target == "prod" else "analysis/output_dev")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"comparison_b_{args.target}.csv"
    out.to_csv(path, index=False)
    print(f"wrote {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
