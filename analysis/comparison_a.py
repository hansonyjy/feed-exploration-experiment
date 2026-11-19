"""Comparison A: the cost of one exploration slot, random vs recommended, in tab 1 (analysis_plan.md).

Primary (D18, D21): for each request with a random item, the random item's value minus the mean of the
recommended items in the same request; averaged within user, then across users (equal user weight).
Session exit (D37): requests with vs without a random item, within user and day, same weighting.

Inference: user-clustered bootstrap, 2,000 resamples, seed 20261115, 95% percentile intervals.
Cross-check (D49): OLS with request fixed effects and no duration-bucket control, weights giving each
user a total weight of 1 (D50), SEs clustered by user. The bucket-controlled regression is reported as a
diagnostic. A headline needs both methods to agree in sign and significance.

Also reported (analysis_plan.md, D20-D24, D51): population-reweighted results, the within-user
robustness check (user x day fixed effects), sensitivity runs excluding the top 0.1% of user-days,
including missing-duration rows (non-duration metrics), excluding AD pool videos, and the
missing-duration rate by arm.

Usage:
  uv run python analysis/comparison_a.py --target dev --dry-run   # bytes of the reads only
  uv run python analysis/comparison_a.py --target dev             # run; output in analysis/output_dev/
Prod (--target prod) runs only when the owner asks; its output goes to exports/.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf
from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED = 20261115
N_BOOT = 2000
ALPHA = 0.05
MAX_READ_BYTES = 10 * 1024**3

ITEM_METRICS = ["effective_view", "naive_completion", "watch_time_ms", "like_", "comment_", "forward_",
                "profile_enter", "new_author_follow", "new_category_effective_view", "hate", "fast_skip"]
DURATION_METRICS = {"effective_view", "naive_completion", "new_category_effective_view"}
NON_DURATION_METRICS = [m for m in ITEM_METRICS if m not in DURATION_METRICS]
DATASETS = {"dev": ("dev", "dev"), "prod": ("staging", "marts")}


# ---------------------------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------------------------
def load_env() -> None:
    env = REPO_ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def queries(project: str, marts: str) -> dict[str, str]:
    item_cols = ", ".join(["request_key", "user_id", "event_date", "is_rand", "has_valid_duration",
                           "duration_bucket", "is_ad_pool_video", "is_top_user_day", *ITEM_METRICS])
    arm_cols = ", ".join(["user_id", "event_date", "is_rand", "has_valid_duration", "is_ad_pool_video",
                          "is_top_user_day", "n_items"]
                         + [f"sum_{m}, n_{m}" for m in ITEM_METRICS])
    return {
        "items": f"select {item_cols} from `{project}.{marts}.mart_random_request_items`",
        "arms": f"select {arm_cols} from `{project}.{marts}.mart_user_day_arm_metrics`",
        "sessions": ("select user_id, event_date, has_random, random_item_valid, random_item_ad, "
                     "is_top_user_day, n_requests, n_session_exit "
                     f"from `{project}.{marts}.mart_session_exit_user_day`"),
    }


def read(client: bigquery.Client, sql: str) -> pd.DataFrame:
    job = client.query(sql, job_config=bigquery.QueryJobConfig(maximum_bytes_billed=MAX_READ_BYTES))
    return job.to_dataframe(create_bqstorage_client=False)


# ---------------------------------------------------------------------------------------------
# Estimation helpers
# ---------------------------------------------------------------------------------------------
def bootstrap(user_values: pd.DataFrame, weighted: bool) -> tuple[float, float, float]:
    """user_values: one row per user with columns mean, sum, n. Returns (estimate, lo, hi).
    Equal user weight: mean of user means. Population-weighted: sum over users / n over users."""
    rng = np.random.default_rng(SEED)
    means = user_values["mean"].to_numpy(float)
    sums = user_values["sum"].to_numpy(float)
    ns = user_values["n"].to_numpy(float)
    idx = rng.integers(0, len(means), size=(N_BOOT, len(means)))
    if weighted:
        est = sums.sum() / ns.sum()
        draws = sums[idx].sum(axis=1) / ns[idx].sum(axis=1)
    else:
        est = means.mean()
        draws = means[idx].mean(axis=1)
    lo, hi = np.percentile(draws, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    return est, lo, hi


def summarize_users(df: pd.DataFrame, value: str) -> pd.DataFrame:
    g = df.groupby("user_id")[value]
    return pd.DataFrame({"mean": g.mean(), "sum": g.sum(), "n": g.count()})


def regress(df: pd.DataFrame, fml: str, weights: str | None) -> tuple[float, float, float]:
    fit = pf.feols(fml, data=df, weights=weights, vcov={"CRV1": "user_id"})
    return float(fit.coef()["is_rand"]), float(fit.se()["is_rand"]), float(fit.pvalue()["is_rand"])


def user_weights(df: pd.DataFrame, base: pd.Series | None = None) -> pd.Series:
    """Observation weights that sum to 1 within each user (D50)."""
    base = pd.Series(1.0, index=df.index) if base is None else base.astype(float)
    return base / base.groupby(df["user_id"]).transform("sum")


# ---------------------------------------------------------------------------------------------
# Comparison A, within request (primary)
# ---------------------------------------------------------------------------------------------
def request_frame(items: pd.DataFrame, variant: str) -> pd.DataFrame:
    df = items
    request_top = df.groupby("request_key")["is_top_user_day"].transform("any")
    random_ad = (df["is_rand"].eq(1) & df["is_ad_pool_video"]).groupby(df["request_key"]).transform("any")
    if variant == "top_user_day_excluded":
        df = df[~request_top]
    elif variant == "ad_pool_excluded":
        df = df[~random_ad]
    if variant != "incl_missing_duration":
        df = df[df["has_valid_duration"]]
    return df


def request_diffs(df: pd.DataFrame, metric: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = df[df[metric].notna()]
    rnd = d[d["is_rand"] == 1][["request_key", "user_id", metric]].rename(columns={metric: "rand"})
    rec = d[d["is_rand"] == 0].groupby("request_key")[metric].agg(rec_mean="mean", n_rec="count")
    out = rnd.merge(rec, on="request_key")
    out = out[out["n_rec"] > 0].copy()
    out["diff"] = out["rand"] - out["rec_mean"]
    sample = d[d["request_key"].isin(out["request_key"])].copy()
    return out, sample


def comparison_request(items: pd.DataFrame, metric: str, variant: str) -> list[dict]:
    diffs, sample = request_diffs(request_frame(items, variant), metric)
    users = summarize_users(diffs, "diff")
    base = summarize_users(diffs, "rec_mean")["mean"].mean()
    rows = []
    for weighting, weighted in (("equal_user", False), ("population", True)):
        if variant != "main" and weighted:
            continue
        est, lo, hi = bootstrap(users, weighted)
        sample = sample.assign(w=user_weights(sample) if not weighted else 1.0)
        coef, se, p = regress(sample, f"{metric} ~ is_rand | request_key", "w")
        row = dict(analysis="A_request", metric=metric, variant=variant, weighting=weighting,
                   estimate=est, ci_low=lo, ci_high=hi, baseline_rec=base, relative=est / base if base else np.nan,
                   n_users=len(users), n_units=len(diffs), reg_coef=coef, reg_se=se, reg_p=p)
        if variant == "main" and not weighted:
            dcoef, dse, dp = regress(sample.dropna(subset=["duration_bucket"]),
                                     f"{metric} ~ is_rand + C(duration_bucket) | request_key", "w")
            row.update(diag_bucket_coef=dcoef, diag_bucket_se=dse, diag_bucket_p=dp)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------------------------
# Session exit (D37): requests with vs without a random item, within user and day
# ---------------------------------------------------------------------------------------------
def comparison_session(sessions: pd.DataFrame, variant: str) -> list[dict]:
    s = sessions
    if variant != "incl_missing_duration":
        s = s[~(s["has_random"] & ~s["random_item_valid"])]
    if variant == "top_user_day_excluded":
        s = s[~s["is_top_user_day"]]
    if variant == "ad_pool_excluded":
        s = s[~(s["has_random"] & s["random_item_ad"])]
    cells = (s.groupby(["user_id", "event_date", "has_random"])[["n_requests", "n_session_exit"]].sum()
             .reset_index())
    cells["rate"] = cells["n_session_exit"] / cells["n_requests"]
    wide = cells.pivot_table(index=["user_id", "event_date"], columns="has_random", values="rate")
    wide = wide.dropna()
    wide.columns = ["rate_without", "rate_with"]
    wide["diff"] = wide["rate_with"] - wide["rate_without"]
    wide = wide.reset_index()
    n_random = (cells[cells["has_random"]].set_index(["user_id", "event_date"])["n_requests"]
                .reindex(pd.MultiIndex.from_frame(wide[["user_id", "event_date"]])).to_numpy())
    wide["n_random"] = n_random
    users = summarize_users(wide, "diff")
    wsum = wide.assign(wd=wide["diff"] * wide["n_random"]).groupby("user_id")
    users_pop = pd.DataFrame({"mean": users["mean"], "sum": wsum["wd"].sum(), "n": wsum["n_random"].sum()})
    base = summarize_users(wide, "rate_without")["mean"].mean()
    keep = cells.merge(wide[["user_id", "event_date"]], on=["user_id", "event_date"])
    keep["user_day"] = keep["user_id"].astype(str) + "_" + keep["event_date"].astype(str)
    keep["is_rand"] = keep["has_random"].astype(int)
    rows = []
    for weighting, weighted, u in (("equal_user", False, users), ("population", True, users_pop)):
        if variant != "main" and weighted:
            continue
        est, lo, hi = bootstrap(u, weighted)
        w = keep["n_requests"].astype(float) if weighted else user_weights(keep, keep["n_requests"])
        coef, se, p = regress(keep.assign(w=w), "rate ~ is_rand | user_day", "w")
        rows.append(dict(analysis="A_session_exit", metric="session_exit", variant=variant,
                         weighting=weighting, estimate=est, ci_low=lo, ci_high=hi, baseline_rec=base,
                         relative=est / base if base else np.nan, n_users=len(users), n_units=len(wide),
                         reg_coef=coef, reg_se=se, reg_p=p))
    return rows


# ---------------------------------------------------------------------------------------------
# Within-user robustness (D18): user-day arm means, user x day fixed effects
# ---------------------------------------------------------------------------------------------
def comparison_within_user(arms: pd.DataFrame, metric: str) -> list[dict]:
    a = arms[arms["has_valid_duration"]]
    cells = a.groupby(["user_id", "event_date", "is_rand"])[[f"sum_{metric}", f"n_{metric}"]].sum().reset_index()
    cells = cells[cells[f"n_{metric}"] > 0]
    cells["mean"] = cells[f"sum_{metric}"] / cells[f"n_{metric}"]
    wide = cells.pivot_table(index=["user_id", "event_date"], columns="is_rand", values="mean").dropna()
    wide.columns = ["rec", "rand"]
    wide["diff"] = wide["rand"] - wide["rec"]
    wide = wide.reset_index()
    users = summarize_users(wide, "diff")
    est, lo, hi = bootstrap(users, weighted=False)
    base = summarize_users(wide, "rec")["mean"].mean()
    keep = cells.merge(wide[["user_id", "event_date"]], on=["user_id", "event_date"])
    keep["user_day"] = keep["user_id"].astype(str) + "_" + keep["event_date"].astype(str)
    w = user_weights(keep, keep[f"n_{metric}"])
    coef, se, p = regress(keep.assign(w=w), "mean ~ is_rand | user_day", "w")
    return [dict(analysis="A_within_user", metric=metric, variant="main", weighting="equal_user",
                 estimate=est, ci_low=lo, ci_high=hi, baseline_rec=base, relative=est / base if base else np.nan,
                 n_users=len(users), n_units=len(wide), reg_coef=coef, reg_se=se, reg_p=p)]


def missing_duration_by_arm(arms: pd.DataFrame) -> pd.DataFrame:
    t = arms.groupby(["is_rand", "has_valid_duration"])["n_items"].sum().unstack(fill_value=0)
    return pd.DataFrame({"is_rand": t.index, "n_items": t.sum(axis=1).to_numpy(),
                         "missing_rate": (t.get(False, 0) / t.sum(axis=1)).to_numpy()})


def agree(row: pd.Series) -> bool:
    sig_boot = row["ci_low"] > 0 or row["ci_high"] < 0
    sig_reg = row["reg_p"] < ALPHA
    return bool(sig_boot and sig_reg and np.sign(row["estimate"]) == np.sign(row["reg_coef"]))


# ---------------------------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=list(DATASETS), default="dev")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    load_env()
    project = os.environ["GCP_PROJECT"]
    client = bigquery.Client(project=project, location=os.environ.get("GCP_LOCATION", "US"))
    _, marts = DATASETS[args.target]
    qs = queries(project, marts)

    total = 0
    for name, sql in qs.items():
        b = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)).total_bytes_processed
        total += b
        print(f"read {name:9s} estimated {b / 1e9:7.3f} GB")
    print(f"read total     estimated {total / 1e9:7.3f} GB")
    if args.dry_run:
        return

    items, arms, sessions = (read(client, qs[k]) for k in ("items", "arms", "sessions"))
    for df in (items,):
        for m in ITEM_METRICS:
            df[m] = df[m].astype(float)
        df["is_rand"] = df["is_rand"].astype(int)
        df["has_valid_duration"] = df["has_valid_duration"].astype(bool)
        df["is_ad_pool_video"] = df["is_ad_pool_video"].astype(bool)
        df["is_top_user_day"] = df["is_top_user_day"].astype(bool)
    for col in ("has_valid_duration", "is_ad_pool_video", "is_top_user_day"):
        arms[col] = arms[col].astype(bool)
    for col in ("has_random", "random_item_valid", "random_item_ad", "is_top_user_day"):
        sessions[col] = sessions[col].astype(bool)
    print(f"loaded {len(items):,} request items, {len(arms):,} user-day arm cells, {len(sessions):,} session cells")

    rows: list[dict] = []
    for m in ITEM_METRICS:
        rows += comparison_request(items, m, "main")
        rows += comparison_request(items, m, "top_user_day_excluded")
        rows += comparison_request(items, m, "ad_pool_excluded")
        if m in NON_DURATION_METRICS:
            rows += comparison_request(items, m, "incl_missing_duration")
        rows += comparison_within_user(arms, m)
        print(f"  done {m}")
    for v in ("main", "top_user_day_excluded", "ad_pool_excluded", "incl_missing_duration"):
        rows += comparison_session(sessions, v)
    print("  done session_exit")

    out = pd.DataFrame(rows)
    out["bootstrap_and_regression_agree"] = out.apply(agree, axis=1)
    out_dir = REPO_ROOT / ("exports" if args.target == "prod" else "analysis/output_dev")
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_dir / f"comparison_a_{args.target}.csv", index=False)
    missing_duration_by_arm(arms).to_csv(out_dir / f"missing_duration_by_arm_{args.target}.csv", index=False)
    print(f"wrote {out_dir.relative_to(REPO_ROOT)}/comparison_a_{args.target}.csv")


if __name__ == "__main__":
    sys.exit(main())
