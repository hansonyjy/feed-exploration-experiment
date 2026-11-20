"""Comparison C: decompose the random-slot gap into content and targeting (analysis_plan.md, D44, D57).

All on tab 1, 2022-04-23 to 05-08, recommended-minus-random (positive = recommended does better):
  total gap     = rec(all)  - rand
  content gap   = rec(all)  - rec(pool)     pool videos vs typical recommended videos
  targeting gap = rec(pool) - rand          the same pool, recommended vs random (Comparison B's question)
The parts add up exactly because all three rates use the same user-days.

Weighting (D57): within day. For each user, each day's arm rates are weighted by the user's random items
that day; user-days without a recommended pool item drop for all three terms (the share of random items
kept is reported). Users are then equally weighted, as in A.

Inference: user-clustered bootstrap (2,000 resamples, seed 20261115; the three gaps share draws).
Cross-check: OLS on user-day cell means with user-day fixed effects, cell weights a_ud / 2 (each user
totals 1), SEs clustered by user; with these weights the coefficient equals the bootstrap's point
estimate. Sensitivity runs as in A.

Also reported (D59 addendum): Comparison A restricted to C's sample (the kept user-days; main run, equal
user weight, bootstrap and request fixed-effects regression as in A), so the C vs A difference splits into
a sample difference (A on all requests vs A on C's sample) and a weighting difference (A on C's sample vs
C's total gap); and C's sample users compared with all users who received a random item (activity-tercile
shares, random items per user). Output: comparison_c_vs_a_<target>.csv and comparison_c_sample_<target>.csv.

Also reported: C's total gap beside A's estimate (sign flipped to recommended-minus-random) and B's
video-weighted estimate beside the targeting gap. They differ by weighting, not by contradiction: A
compares items in the same request, C compares arm rates over a user's day, B weights each video equally.

Usage:
  uv run python analysis/comparison_c.py --target dev [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd
import pyfixest as pf
from google.cloud import bigquery

from comparison_a import (ALPHA, DATASETS, ITEM_METRICS, N_BOOT, NON_DURATION_METRICS, REPO_ROOT, SEED,
                          agree, comparison_request, load_env, read)
from comparison_a import queries as a_queries

TERMS = {"total": ("rec_all", "rand"), "content": ("rec_all", "rec_pool"), "targeting": ("rec_pool", "rand")}


def query(project: str, marts: str) -> str:
    cols = ", ".join(["user_id", "event_date", "item_group", "has_valid_duration", "is_ad_pool_video",
                      "is_top_user_day", "n_items"] + [f"sum_{m}, n_{m}" for m in ITEM_METRICS])
    return f"select {cols} from `{project}.{marts}.mart_decomposition_user_day`"


def user_day_rates(cells: pd.DataFrame, metric: str, variant: str) -> tuple[pd.DataFrame, float]:
    c = cells
    if variant == "top_user_day_excluded":
        c = c[~c["is_top_user_day"]]
    elif variant == "ad_pool_excluded":
        c = c[~((c["item_group"] == "rand") & c["is_ad_pool_video"])]
    if variant != "incl_missing_duration":
        c = c[c["has_valid_duration"]]
    g = c.groupby(["user_id", "event_date", "item_group"])[[f"sum_{metric}", f"n_{metric}"]].sum()
    s = g[f"sum_{metric}"].unstack(fill_value=0)
    n = g[f"n_{metric}"].unstack(fill_value=0)
    for grp in ("rand", "rec_pool", "rec_nonpool"):
        s[grp] = s.get(grp, 0)
        n[grp] = n.get(grp, 0)
    s["rec_all"], n["rec_all"] = s["rec_pool"] + s["rec_nonpool"], n["rec_pool"] + n["rec_nonpool"]
    rand_total = n["rand"].sum()
    keep = (n["rand"] > 0) & (n["rec_pool"] > 0)
    s, n = s[keep], n[keep]
    out = pd.DataFrame({grp: s[grp] / n[grp] for grp in ("rand", "rec_pool", "rec_all")})
    out["n_rand"] = n["rand"]
    out = out.reset_index()
    out["a"] = out["n_rand"] / out.groupby("user_id")["n_rand"].transform("sum")
    return out, (out["n_rand"].sum() / rand_total if rand_total else np.nan)


def user_gaps(ud: pd.DataFrame) -> pd.DataFrame:
    r = ud[["rand", "rec_pool", "rec_all"]].mul(ud["a"], axis=0).groupby(ud["user_id"]).sum()
    return pd.DataFrame({t: r[hi] - r[lo] for t, (hi, lo) in TERMS.items()} | {"rec_all": r["rec_all"]})


def bootstrap(users: pd.DataFrame) -> dict[str, tuple[float, float]]:
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(users), size=(N_BOOT, len(users)))
    out = {}
    for t in TERMS:
        draws = users[t].to_numpy(float)[idx].mean(axis=1)
        out[t] = tuple(np.percentile(draws, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)]))
    return out


def regress(ud: pd.DataFrame, term: str) -> tuple[float, float, float]:
    hi, lo = TERMS[term]
    long = pd.concat([ud.assign(y=ud[hi], is_rand=1), ud.assign(y=ud[lo], is_rand=0)], ignore_index=True)
    long["user_day"] = long["user_id"].astype(str) + "_" + long["event_date"].astype(str)
    long["w"] = long["a"] / 2
    # "is_rand" names the indicator so comparison_a.agree() applies: 1 = the first group of the term.
    fit = pf.feols("y ~ is_rand | user_day", data=long, weights="w", vcov={"CRV1": "user_id"})
    return float(fit.coef()["is_rand"]), float(fit.se()["is_rand"]), float(fit.pvalue()["is_rand"])


def run(cells: pd.DataFrame, metric: str, variant: str) -> list[dict]:
    ud, kept = user_day_rates(cells, metric, variant)
    users = user_gaps(ud)
    cis = bootstrap(users)
    base = users["rec_all"].mean()
    rows = []
    for t in TERMS:
        coef, se, p = regress(ud, t)
        est = users[t].mean()
        rows.append(dict(analysis="C_decomposition", metric=metric, variant=variant, term=t,
                         weighting="equal_user_day_weighted", estimate=est, ci_low=cis[t][0], ci_high=cis[t][1],
                         baseline_rec_all=base, relative_to_rec_all=est / base if base else np.nan,
                         n_users=len(users), n_user_days=len(ud), share_random_items_kept=kept,
                         reg_coef=coef, reg_se=se, reg_p=p))
    return rows


def a_on_c_sample(cells: pd.DataFrame, items: pd.DataFrame, metric: str) -> tuple[dict, pd.DataFrame]:
    """Comparison A (main run, equal user weight) on the requests of C's kept user-days for this metric."""
    ud, _ = user_day_rates(cells, metric, "main")
    kept = ud[["user_id", "event_date"]].astype(str).drop_duplicates()
    key = items["user_id"].astype(str) + "|" + items["event_date"].astype(str)
    sub = items[key.isin(set(kept["user_id"] + "|" + kept["event_date"]))]
    row = [r for r in comparison_request(sub, metric, "main") if r["weighting"] == "equal_user"][0]
    row.update(analysis="A_on_C_sample")
    return row, ud


def sample_profile(cells: pd.DataFrame, ud: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    """C's sample users (effective view, main run) vs all users with a random item: activity-tercile
    shares and random items per user (all random tab-1 items in the window)."""
    rand_per_user = cells[cells["item_group"] == "rand"].groupby("user_id")["n_items"].sum()
    groups = {"all_users_with_random": rand_per_user.index, "c_sample_users": pd.Index(ud["user_id"].unique())}
    kept_per_user = ud.groupby("user_id")["n_rand"].sum()
    rows = []
    for name, users in groups.items():
        r = rand_per_user.reindex(users)
        terc = profile.set_index("user_id")["activity_tercile"].reindex(users).fillna("missing")
        row = dict(group=name, n_users=len(users), random_items_per_user_mean=r.mean(),
                   random_items_per_user_median=r.median())
        if name == "c_sample_users":
            row.update(kept_random_items_per_user_mean=kept_per_user.mean(),
                       kept_random_items_per_user_median=kept_per_user.median())
        row.update({f"share_activity_{k}": v for k, v in terc.value_counts(normalize=True).sort_index().items()})
        rows.append(row)
    return pd.DataFrame(rows)


def attach_a_and_b(out: pd.DataFrame, target: str) -> pd.DataFrame:
    """A's request-level estimate beside the total gap and B's beside the targeting gap, both flipped to
    recommended-minus-random. Missing files leave the columns empty."""
    base = REPO_ROOT / ("exports" if target == "prod" else "analysis/output_dev")
    out["a_estimate_rec_minus_rand"] = np.nan
    out["b_estimate_rec_minus_rand"] = np.nan
    keys = ["metric", "variant"]
    a_path, b_path = base / f"comparison_a_{target}.csv", base / f"comparison_b_{target}.csv"
    if a_path.exists():
        a = pd.read_csv(a_path)
        a = a[(a["analysis"] == "A_request") & (a["weighting"] == "equal_user")][keys + ["estimate"]]
        m = out[keys].merge(a, on=keys, how="left")["estimate"].to_numpy()
        out.loc[out["term"] == "total", "a_estimate_rec_minus_rand"] = -m[out["term"].eq("total").to_numpy()]
    if b_path.exists():
        b = pd.read_csv(b_path)[keys + ["estimate"]]
        m = out[keys].merge(b, on=keys, how="left")["estimate"].to_numpy()
        out.loc[out["term"] == "targeting", "b_estimate_rec_minus_rand"] = -m[out["term"].eq("targeting").to_numpy()]
    return out


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
    a_items_sql = a_queries(project, DATASETS[args.target][1])["items"]
    profile_sql = (f"select user_id, activity_tercile from `{project}.{DATASETS[args.target][0]}.int_user_pre_profile`")
    for name, q in (("A items", a_items_sql), ("profile", profile_sql)):
        b = client.query(q, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)).total_bytes_processed
        print(f"read {name} estimated {b / 1e9:.3f} GB")
    if args.dry_run:
        return
    cells = read(client, sql)
    for c in ("has_valid_duration", "is_ad_pool_video", "is_top_user_day"):
        cells[c] = cells[c].astype(bool)
    for m in ITEM_METRICS:
        cells[f"sum_{m}"] = cells[f"sum_{m}"].astype(float)
        cells[f"n_{m}"] = cells[f"n_{m}"].astype(float)
    print(f"loaded {len(cells):,} user-day cells")

    rows = []
    for m in ITEM_METRICS:
        variants = ["main", "top_user_day_excluded", "ad_pool_excluded"]
        if m in NON_DURATION_METRICS:
            variants.append("incl_missing_duration")
        for v in variants:
            rows += run(cells, m, v)
        print(f"  done {m}")
    out = pd.DataFrame(rows)
    out["bootstrap_and_regression_agree"] = out.apply(agree, axis=1)
    wide = out.pivot_table(index=["metric", "variant"], columns="term", values="estimate")
    gap = (wide["total"] - wide["content"] - wide["targeting"]).abs().max()
    print(f"additivity: max |total - content - targeting| = {gap:.2e}")
    out = attach_a_and_b(out, args.target)
    out_dir = REPO_ROOT / ("exports" if args.target == "prod" else "analysis/output_dev")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"comparison_c_{args.target}.csv"
    out.to_csv(path, index=False)
    print(f"wrote {path.relative_to(REPO_ROOT)}")

    # D59 addendum: A on C's sample, and who is in C's sample.
    items = read(client, a_items_sql)
    for m in ITEM_METRICS:
        items[m] = items[m].astype(float)
    items["is_rand"] = items["is_rand"].astype(int)
    for c in ("has_valid_duration", "is_ad_pool_video", "is_top_user_day"):
        items[c] = items[c].astype(bool)
    profile = read(client, profile_sql)
    a_rows, ud_ev = [], None
    for m in ITEM_METRICS:
        row, ud = a_on_c_sample(cells, items, m)
        a_rows.append(row)
        if m == "effective_view":
            ud_ev = ud
    a_c = pd.DataFrame(a_rows)
    a_c["bootstrap_and_regression_agree"] = a_c.apply(agree, axis=1)
    main_total = out[(out["variant"] == "main") & (out["term"] == "total")].set_index("metric")
    vs = a_c.set_index("metric")[["estimate", "ci_low", "ci_high", "reg_coef", "reg_p", "n_users", "n_units",
                                   "bootstrap_and_regression_agree"]].add_prefix("a_on_c_sample_")
    vs["a_all_requests"] = -main_total["a_estimate_rec_minus_rand"]
    vs["c_total_gap_rand_minus_rec"] = -main_total["estimate"]
    vs["sample_difference"] = vs["a_on_c_sample_estimate"] - vs["a_all_requests"]
    vs["weighting_difference"] = vs["c_total_gap_rand_minus_rec"] - vs["a_on_c_sample_estimate"]
    vs.reset_index().to_csv(out_dir / f"comparison_c_vs_a_{args.target}.csv", index=False)
    sample_profile(cells, ud_ev, profile).to_csv(out_dir / f"comparison_c_sample_{args.target}.csv", index=False)
    print(f"wrote comparison_c_vs_a_{args.target}.csv and comparison_c_sample_{args.target}.csv")


if __name__ == "__main__":
    sys.exit(main())
