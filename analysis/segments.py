"""Comparison A by segment, with Benjamini-Hochberg and Benjamini-Yekutieli (analysis_plan.md; D57, D59).

Segments are pre-period user segments (activity tercile, active group, tenure band, follow band) and the
random item's segments (duration bucket, category), after the merges in segment_merge_map (D39, D40,
D58). Main run only (random item and at least one recommended item with a valid duration), equal user
weight, metrics: effective view, new-author follow, new-category effective view, hate, fast skip.

Per segment:
- effect vs zero: as A (user-clustered bootstrap; request fixed-effects regression, SEs by user);
- contrast (the H4 test): segment minus the rest of its dimension, on merged segments. Bootstrap resamples
  users jointly for both sides; regression adds is_rand x in_segment with request fixed effects.
BH (q = 0.10) and BY run per metric across all contrasts of all dimensions, separately on regression and
bootstrap p-values. A contrast is a finding if it passes in both with agreeing signs, otherwise a lead.
Contrasts within a dimension are negatively correlated (each segment is in the others' rest); BY is valid
under any dependence and is reported as robustness.

Usage:
  uv run python analysis/segments.py --synthetic            # code check on generated data; reads nothing
  uv run python analysis/segments.py --target prod [--dry-run]
The prod run refuses to start unless dbt/seeds/segment_merge_map.csv is committed and unchanged (D57).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import pyfixest as pf
from google.cloud import bigquery

from comparison_a import ALPHA, DATASETS, N_BOOT, REPO_ROOT, SEED, load_env, read, request_diffs, user_weights

METRICS = ["effective_view", "new_author_follow", "new_category_effective_view", "hate", "fast_skip"]
USER_DIMS = ["activity_tercile", "active_group", "tenure_band", "follow_band"]
ITEM_DIMS = ["duration_bucket", "category_segment"]
Q = 0.10
MAP_PATH = REPO_ROOT / "dbt/seeds/segment_merge_map.csv"


# ---------------------------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------------------------
def queries(project: str, staging: str, marts: str) -> dict[str, str]:
    cols = ", ".join(["request_key", "user_id", "is_rand", "has_valid_duration", *METRICS])
    return {
        "items": f"select {cols} from `{project}.{marts}.mart_random_request_items` where has_valid_duration",
        "item_segments": ("select request_key, cast(duration_bucket as string) as duration_bucket, "
                          f"category_segment from `{project}.{staging}.int_random_item_segments`"),
        "profile": ("select user_id, activity_tercile, active_group, tenure_band, follow_band "
                    f"from `{project}.{staging}.int_user_pre_profile`"),
    }


def require_committed_map() -> None:
    rel = str(MAP_PATH.relative_to(REPO_ROOT))
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO_ROOT, capture_output=True)
    clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=REPO_ROOT)
    if tracked.returncode != 0 or clean.returncode != 0 or len(MAP_PATH.read_text().splitlines()) < 2:
        sys.exit(f"{rel} must be committed and unchanged before any segment outcome is read (D57)")


def label_requests(items: pd.DataFrame, item_segments: pd.DataFrame, profile: pd.DataFrame,
                   merge_map: pd.DataFrame) -> pd.DataFrame:
    """One row per request: user_id and the merged segment of every dimension (NaN if excluded)."""
    req = items[items["is_rand"] == 1][["request_key", "user_id"]].drop_duplicates("request_key")
    req = req.merge(profile, on="user_id", how="left").merge(item_segments, on="request_key", how="left")
    for dim in USER_DIMS + ITEM_DIMS:
        m = merge_map[merge_map["dimension"] == dim].set_index("segment")["final_segment"]
        req[dim] = req[dim].astype("string").map(m)
    return req


# ---------------------------------------------------------------------------------------------
# Estimation
# ---------------------------------------------------------------------------------------------
def pct_ci(draws: np.ndarray) -> tuple[float, float]:
    lo, hi = np.percentile(draws, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    return float(lo), float(hi)


def boot_p(draws: np.ndarray) -> float:
    p = 2 * min((draws <= 0).mean(), (draws >= 0).mean())
    return float(max(p, 1 / len(draws)))


def boot_effect(user_means: np.ndarray) -> np.ndarray:
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(user_means), size=(N_BOOT, len(user_means)))
    return user_means[idx].mean(axis=1)


def boot_contrast(seg: np.ndarray, rest: np.ndarray) -> np.ndarray:
    """seg, rest: per-user means on each side (NaN where the user has no requests on that side)."""
    rng = np.random.default_rng(SEED)
    n = len(seg)
    seg0, rest0 = np.nan_to_num(seg), np.nan_to_num(rest)
    has_s, has_r = ~np.isnan(seg), ~np.isnan(rest)
    out = []
    for start in range(0, N_BOOT, 250):
        idx = rng.integers(0, n, size=(min(250, N_BOOT - start), n))
        out.append(seg0[idx].sum(1) / has_s[idx].sum(1) - rest0[idx].sum(1) / has_r[idx].sum(1))
    return np.concatenate(out)


def fdr(p: np.ndarray, yekutieli: bool = False) -> np.ndarray:
    """Adjusted p-values (q-values): Benjamini-Hochberg, or Benjamini-Yekutieli if yekutieli."""
    p = np.asarray(p, float)
    m = len(p)
    order = np.argsort(p)
    c = np.sum(1.0 / np.arange(1, m + 1)) if yekutieli else 1.0
    adj = p[order] * m * c / np.arange(1, m + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.minimum(adj, 1.0)
    return out


def segment_rows(diffs: pd.DataFrame, sample: pd.DataFrame, req: pd.DataFrame, metric: str,
                 dim: str) -> list[dict]:
    d = diffs.merge(req[["request_key", dim]], on="request_key").dropna(subset=[dim])
    s = sample.merge(req[["request_key", dim]], on="request_key").dropna(subset=[dim])
    segments = sorted(d[dim].unique())
    rows = []
    for seg in segments:
        in_seg = d[dim] == seg
        u_seg = d[in_seg].groupby("user_id")["diff"].mean()
        draws = boot_effect(u_seg.to_numpy(float))
        base = d[in_seg].groupby("user_id")["rec_mean"].mean().mean()
        ss = s[s[dim] == seg]
        fit = pf.feols(f"{metric} ~ is_rand | request_key", data=ss.assign(w=user_weights(ss)), weights="w",
                       vcov={"CRV1": "user_id"})
        row = dict(dimension=dim, segment=seg, metric=metric, n_users=len(u_seg), n_requests=int(in_seg.sum()),
                   estimate=float(u_seg.mean()), ci_low=pct_ci(draws)[0], ci_high=pct_ci(draws)[1],
                   baseline_rec=float(base), relative=float(u_seg.mean() / base) if base else np.nan,
                   reg_coef=float(fit.coef()["is_rand"]), reg_p=float(fit.pvalue()["is_rand"]))
        if len(segments) > 1:
            u_rest = d[~in_seg].groupby("user_id")["diff"].mean()
            users = u_seg.index.union(u_rest.index)
            cdraws = boot_contrast(u_seg.reindex(users).to_numpy(float), u_rest.reindex(users).to_numpy(float))
            side = s[dim].eq(seg).astype(int)
            w = 1.0 / s.groupby([s["user_id"], side])["user_id"].transform("count")
            cfit = pf.feols(f"{metric} ~ is_rand + is_rand:in_seg | request_key",
                            data=s.assign(in_seg=side, w=w), weights="w", vcov={"CRV1": "user_id"})
            name = "is_rand:in_seg"
            row.update(contrast=float(u_seg.mean() - u_rest.mean()), contrast_ci_low=pct_ci(cdraws)[0],
                       contrast_ci_high=pct_ci(cdraws)[1], contrast_boot_p=boot_p(cdraws),
                       contrast_reg_coef=float(cfit.coef()[name]), contrast_reg_se=float(cfit.se()[name]),
                       contrast_reg_p=float(cfit.pvalue()[name]))
        rows.append(row)
    return rows


def add_fdr(out: pd.DataFrame) -> pd.DataFrame:
    out = out.copy()
    for col in ("bh_q_reg", "bh_q_boot", "by_q_reg", "by_q_boot"):
        out[col] = np.nan
    for metric, g in out.dropna(subset=["contrast"]).groupby("metric"):
        i = g.index
        out.loc[i, "bh_q_reg"] = fdr(g["contrast_reg_p"].to_numpy())
        out.loc[i, "bh_q_boot"] = fdr(g["contrast_boot_p"].to_numpy())
        out.loc[i, "by_q_reg"] = fdr(g["contrast_reg_p"].to_numpy(), yekutieli=True)
        out.loc[i, "by_q_boot"] = fdr(g["contrast_boot_p"].to_numpy(), yekutieli=True)
    same_sign = np.sign(out["contrast"]) == np.sign(out["contrast_reg_coef"])
    out["finding_bh"] = (out["bh_q_reg"] <= Q) & (out["bh_q_boot"] <= Q) & same_sign
    out["finding_by"] = (out["by_q_reg"] <= Q) & (out["by_q_boot"] <= Q) & same_sign
    out["lead_bh"] = out["contrast"].notna() & ~out["finding_bh"] & ((out["bh_q_reg"] <= Q) | (out["bh_q_boot"] <= Q)
                                                                     | (out["contrast_reg_p"] < ALPHA))
    sig_boot = (out["ci_low"] > 0) | (out["ci_high"] < 0)
    out["effect_agree"] = sig_boot & (out["reg_p"] < ALPHA) & (np.sign(out["estimate"]) == np.sign(out["reg_coef"]))
    return out


def analyse(items: pd.DataFrame, req: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric in METRICS:
        diffs, sample = request_diffs(items, metric)
        for dim in USER_DIMS + ITEM_DIMS:
            rows += segment_rows(diffs, sample, req, metric, dim)
        print(f"  done {metric}")
    out = add_fdr(pd.DataFrame(rows))
    merged_category = (out["dimension"] == "category_segment") & out["segment"].astype(str).str.contains(r"\+")
    out["interpretable"] = ~merged_category
    out["segment_note"] = np.where(merged_category, "power-based grouping (D40); no topical meaning", "")
    return out


# ---------------------------------------------------------------------------------------------
# Synthetic check: planted heterogeneity, no reads
# ---------------------------------------------------------------------------------------------
def synthetic() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(1)
    n_users, n_req = 1500, 30
    users = pd.DataFrame({"user_id": np.arange(n_users),
                          "activity_tercile": rng.choice(["1", "2", "3"], n_users),
                          "active_group": rng.choice(["high_active", "full_active"], n_users),
                          "tenure_band": rng.choice(["a", "b"], n_users), "follow_band": rng.choice(["x", "y"], n_users)})
    rq = pd.DataFrame({"user_id": np.repeat(users.user_id, n_req)})
    rq["request_key"] = np.arange(len(rq)).astype(str)
    rq["duration_bucket"] = rng.choice(["1", "2"], len(rq))
    rq["category_segment"] = rng.choice(["c1", "c2", "other"], len(rq))
    rq = rq.merge(users, on="user_id")
    # Planted: random items lose 0.30 effective view, 0.10 more in activity tercile 1 and in bucket 2.
    effect = -0.30 - 0.10 * (rq["activity_tercile"] == "1") - 0.10 * (rq["duration_bucket"] == "2")
    rows = []
    for k in range(5):
        is_rand = int(k == 0)
        p = 0.55 + is_rand * effect
        rows.append(pd.DataFrame({"request_key": rq["request_key"], "user_id": rq["user_id"], "is_rand": is_rand,
                                  "has_valid_duration": True,
                                  **{m: (rng.random(len(rq)) < (p if m == "effective_view" else 0.2)).astype(float)
                                     for m in METRICS}}))
    items = pd.concat(rows, ignore_index=True)
    req = rq[["request_key", "user_id", *USER_DIMS, *ITEM_DIMS]]
    return items, req


# ---------------------------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=list(DATASETS), default="prod")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    if args.synthetic:
        items, req = synthetic()
        out = analyse(items, req)
        path = REPO_ROOT / "analysis/output_dev/segments_synthetic.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(path, index=False)
        ev = out[out.metric == "effective_view"]
        print(ev[["dimension", "segment", "estimate", "contrast", "contrast_reg_coef", "bh_q_reg", "bh_q_boot",
                  "finding_bh", "finding_by"]].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
        print(f"wrote {path.relative_to(REPO_ROOT)} (planted: tercile 1 and bucket 2 lose 0.10 more)")
        return
    if args.target == "dev":
        sys.exit("segment outcomes are read on prod only, with the committed merge map (D57); use --synthetic")
    require_committed_map()
    load_env()
    project = os.environ["GCP_PROJECT"]
    client = bigquery.Client(project=project, location=os.environ.get("GCP_LOCATION", "US"))
    staging, marts = DATASETS[args.target]
    qs = queries(project, staging, marts)
    total = sum(client.query(q, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
                .total_bytes_processed for q in qs.values())
    print(f"reads estimated {total / 1e9:.3f} GB")
    if args.dry_run:
        return
    items, item_segments, profile = (read(client, qs[k]) for k in ("items", "item_segments", "profile"))
    for m in METRICS:
        items[m] = items[m].astype(float)
    items["is_rand"] = items["is_rand"].astype(int)
    merge_map = pd.read_csv(MAP_PATH, dtype=str)
    req = label_requests(items, item_segments, profile, merge_map)
    out = analyse(items, req)
    path = REPO_ROOT / "exports/segments_prod.csv"
    out.to_csv(path, index=False)
    print(f"wrote {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
