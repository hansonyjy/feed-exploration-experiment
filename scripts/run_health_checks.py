"""Run the Phase 0 health checks (analysis/health_checks/*.sql) and judge them against the approved
pass criteria in docs/data_quality.md.

Each SQL file declares `-- scope: full` (full raw tables) or `-- scope: dev5` (5% user-sample logs).
Placeholders: {raw} dataset, {pre} {treat} {rnd} log tables for that scope, {rnd_full} the full random log.

Every query is dry-run first; the estimated bytes are printed, and a query over 50 GB is refused
(CLAUDE.md). Each real run uses maximum_bytes_billed = max(1.25 x estimate, 1 GiB).

Usage:
  uv run python scripts/run_health_checks.py --dry-run     # bytes only, runs nothing
  uv run python scripts/run_health_checks.py               # run all, write exports/health/
  uv run python scripts/run_health_checks.py --only hc01   # one check
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = REPO_ROOT / "analysis" / "health_checks"
OUT_DIR = REPO_ROOT / "exports" / "health"
MAX_BYTES = 50 * 10**9  # ask before anything larger (CLAUDE.md)


def load_env() -> None:
    env = REPO_ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def render(sql: str, project: str) -> tuple[str, str]:
    match = re.search(r"^-- scope: (full|dev5)\s*$", sql, re.M)
    if not match:
        raise ValueError("missing '-- scope: full|dev5' header")
    scope = match.group(1)
    suffix = "" if scope == "full" else "_dev5"
    raw = f"`{project}.raw`"
    names = {
        "raw": raw,
        "pre": f"`{project}.raw.log_standard_pre{suffix}`",
        "treat": f"`{project}.raw.log_standard_treat{suffix}`",
        "rnd": f"`{project}.raw.log_random_treat{suffix}`",
        "rnd_full": f"`{project}.raw.log_random_treat`",
    }
    # Replace only {name} placeholders we know, leaving any other braces alone.
    rendered = re.sub(r"\{(raw|pre|treat|rnd|rnd_full)\}", lambda m: names[m.group(1)], sql)
    return scope, fix_raw_refs(rendered, project)


def fix_raw_refs(sql: str, project: str) -> str:
    # {raw}.table renders as `project.raw`.table; turn it into `project.raw.table`.
    return re.sub(rf"`{re.escape(project)}\.raw`\.(\w+)", rf"`{project}.raw.\1`", sql)


# ---------------------------------------------------------------------------------------------
# Pass criteria (docs/data_quality.md, approved 2026-11-16). Each returns a list of
# (criterion, value, passed, severity) rows.
# ---------------------------------------------------------------------------------------------
def judge_hc01(rows):
    overall = next(r for r in rows if r["dimension"] == "overall")
    share = overall["n_random"] / overall["n_exposures"]
    out = [("overall random share (reported, no band)", f"{share:.4%}", None, "info")]
    limits = {"day": 0.20, "activity_tercile": 0.20, "active_group": 0.20, "tenure_band": 0.20, "tab": 0.50}
    for dim, tol in limits.items():
        cells = [r for r in rows if r["dimension"] == dim]
        judged = [r for r in cells if r["n_exposures"] * share >= 1000]
        worst = max(judged, key=lambda r: abs(r["n_random"] / r["n_exposures"] / share - 1), default=None)
        if worst is None:
            out.append((f"{dim}: no cell has >= 1,000 expected random", "-", None, "info"))
            continue
        dev = worst["n_random"] / worst["n_exposures"] / share - 1
        sev = "non-blocking" if dim == "tab" else "blocking"
        out.append((f"{dim}: max relative deviation within ±{tol:.0%} ({len(judged)} of {len(cells)} cells judged)",
                    f"{dev:+.1%} (cell {worst['cell']})", abs(dev) <= tol, sev))
    return out


def judge_hc02a(rows):
    r = rows[0]
    return [
        ("distinct pool videos 7,500-7,583", f"{r['n_pool_videos']:,}", 7500 <= r["n_pool_videos"] <= 7583, "non-blocking"),
        ("exposures per video CV <= 0.25", f"{r['cv_exposures']:.3f}", r["cv_exposures"] <= 0.25, "non-blocking"),
        ("max/min exposures <= 3", f"{r['max_min_ratio']:.2f} ({r['min_exposures']}-{r['max_exposures']})",
         r["max_min_ratio"] <= 3, "non-blocking"),
    ]


def judge_hc02b(rows):
    return [(f"{r['video_set']}: attributes (reported)",
             f"n={r['n_videos']:,}, normal={r['share_normal']:.3f}, ad={r['share_ad']:.4f}, "
             f"median dur={r['duration_ms_deciles'][5]:.0f} ms, upload {r['min_upload_dt']}..{r['max_upload_dt']}, "
             f"uploaded in window={r['share_uploaded_in_window']:.3f}", None, "info") for r in rows]


def judge_hc03(rows):
    r = rows[0]
    a = r["n_treatment_users_in_pre"] / r["n_treatment_users"]
    b = r["n_random_users_with_standard"] / r["n_random_users"]
    return [
        ("treatment users found in pre-period >= 95% (blocking < 80%)", f"{a:.2%}", a >= 0.95,
         "blocking" if a < 0.80 else "non-blocking"),
        ("random-log users with standard exposures >= 99%", f"{b:.2%}", b >= 0.99, "non-blocking"),
    ]


def judge_hc04(rows):
    out = []
    for r in rows:
        n = r["n_rows"]
        p = r["period"]
        out += [
            (f"{p}: bad duration <= 0.5%", f"{r['n_bad_duration'] / n:.3%}", r["n_bad_duration"] / n <= 0.005, "non-blocking"),
            (f"{p}: negative play time = 0", f"{r['n_negative_play']:,}", r["n_negative_play"] == 0, "non-blocking"),
            (f"{p}: play > 5x duration <= 1%", f"{r['n_play_over_5x'] / n:.3%}", r["n_play_over_5x"] / n <= 0.01, "non-blocking"),
            (f"{p}: log duration within 1 s of feature duration >= 99%",
             f"{r['n_duration_within_1s'] / r['n_with_video_features']:.2%}",
             r["n_duration_within_1s"] / r["n_with_video_features"] >= 0.99, "non-blocking"),
        ]
    return out


def judge_hc05(rows):
    out = []
    for r in rows:
        n = r["n_rows"]
        out += [
            (f"{r['source']}: exact duplicate rows <= 0.1%",
             f"{r['n_exact_duplicate_rows']:,} ({r['n_exact_duplicate_rows'] / n:.3%})",
             r["n_exact_duplicate_rows"] / n <= 0.001, "non-blocking"),
            (f"{r['source']}: rows in conflicting keys <= 0.1%",
             f"{r['n_rows_in_conflicting_keys']:,} rows in {r['n_conflicting_keys']:,} keys "
             f"({r['n_rows_in_conflicting_keys'] / n:.3%})",
             r["n_rows_in_conflicting_keys"] / n <= 0.001, "non-blocking"),
        ]
    return out


def judge_hc06(rows):
    r = rows[0]
    u = r["n_flagged_users"] / r["n_users"]
    e = r["n_flagged_exposures"] / r["n_exposures"]
    return [
        ("user-day exposures p50 / p99 / p99.9 / max (reported)",
         f"{r['user_day_p50']} / {r['user_day_p99']} / {r['user_day_p999']} / {r['user_day_max']}", None, "info"),
        ("flagged users <= 0.5%", f"{r['n_flagged_users']:,} ({u:.2%})", u <= 0.005, "non-blocking"),
        ("flagged users' exposures <= 2%", f"{e:.2%}", e <= 0.02, "non-blocking"),
    ]


def judge_hc07(rows):
    return [("random rows by tab (reported)",
             ", ".join(f"tab {r['tab']}: {r['n_random']:,} ({r['share_of_random']:.1%})" for r in rows), None, "info")]


def judge_hc09(rows):
    r = rows[0]
    overlap = r["n_random_keys_in_standard"] / r["n_random_keys"]
    clear = overlap <= 0.01 or overlap >= 0.99
    return [
        ("is_rand = 0 on every standard-log row",
         f"pre {r['pre_n_is_rand_not_0']:,} / treat {r['treat_n_is_rand_not_0']:,} rows not 0",
         r["pre_n_is_rand_not_0"] == 0 and r["treat_n_is_rand_not_0"] == 0, "blocking"),
        ("random keys found in standard treatment log: ~0% or ~100%",
         f"{r['n_random_keys_in_standard']:,} of {r['n_random_keys']:,} ({overlap:.3%}); "
         f"same user+time_ms: {r['n_random_user_time_in_standard']:,}", clear, "blocking"),
    ]


WINDOWS = {"pre": ("2022-04-08", "2022-04-21"), "treat": ("2022-04-22", "2022-05-08"), "rnd": ("2022-04-22", "2022-05-08")}


def judge_hc10(rows):
    out = []
    for r in rows:
        lo, hi = WINDOWS[r["source"]]
        out.append((f"{r['source']}: event_date range matches window {lo}..{hi}",
                    f"{r['min_event_date']}..{r['max_event_date']}",
                    str(r["min_event_date"]) == lo and str(r["max_event_date"]) == hi, "blocking"))
        m = r["n_date_match_shanghai"] / r["n_rows"]
        out.append((f"{r['source']}: event_date = Shanghai date of time_ms >= 99.9%",
                    f"{m:.3%} (UTC {r['n_date_match_utc'] / r['n_rows']:.2%}; hour match "
                    f"{r['n_hour_match_shanghai'] / r['n_rows']:.2%}; hourmin with minutes {r['n_hourmin_with_minutes']:,})",
                    m >= 0.999, "non-blocking"))
    return out


def judge_hc11(rows):
    r = rows[0]
    u = r["n_log_users_with_features"] / r["n_log_users"]
    v = r["n_log_videos_with_features"] / r["n_log_videos"]
    c = r["n_treat_videos_with_category"] / r["n_treat_videos"]
    t = r["n_l1_in_tag"] / r["n_tag_comparable"] if r["n_tag_comparable"] else 0.0
    return [
        ("log users in user_features >= 99.9%", f"{u:.3%}", u >= 0.999, "blocking"),
        ("log videos in video_features_basic >= 99%", f"{v:.3%}", v >= 0.99, "non-blocking"),
        ("treatment videos in category file >= 95%", f"{c:.3%}", c >= 0.95, "non-blocking"),
        ("first-level category id in tag ids >= 90%", f"{t:.2%} of {r['n_tag_comparable']:,}", t >= 0.90, "non-blocking"),
    ]


JUDGES = {
    "hc01": judge_hc01, "hc02a": judge_hc02a, "hc02b": judge_hc02b, "hc03": judge_hc03, "hc04": judge_hc04,
    "hc05": judge_hc05, "hc06": judge_hc06, "hc07": judge_hc07, "hc09": judge_hc09, "hc10": judge_hc10,
    "hc11": judge_hc11,
}


def to_jsonable(v):
    if isinstance(v, (list, tuple)):
        return [to_jsonable(x) for x in v]
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print estimated bytes only")
    parser.add_argument("--only", help="run only checks whose file name starts with this")
    args = parser.parse_args()

    load_env()
    project = os.environ["GCP_PROJECT"]
    client = bigquery.Client(project=project, location=os.environ.get("GCP_LOCATION", "US"))
    files = sorted(SQL_DIR.glob("hc*.sql"))
    if args.only:
        files = [f for f in files if f.name.startswith(args.only)]

    # 1. Dry-run everything first.
    plan = []
    for f in files:
        scope, sql = render(f.read_text(), project)
        job = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
        est = job.total_bytes_processed
        plan.append((f, scope, sql, est))
        print(f"{f.stem:32s} scope={scope:5s} estimated {est / 1e9:8.3f} GB")
    total = sum(p[3] for p in plan)
    print(f"{'total':32s}            estimated {total / 1e9:8.3f} GB")
    too_big = [p[0].stem for p in plan if p[3] > MAX_BYTES]
    if too_big:
        sys.exit(f"refusing: over 50 GB: {too_big}")
    if args.dry_run:
        return

    # 2. Run, save results, judge.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {}
    for f, scope, sql, est in plan:
        cap = max(int(est * 1.25), 2**30)
        job = client.query(sql, job_config=bigquery.QueryJobConfig(maximum_bytes_billed=cap))
        rows = [dict(r.items()) for r in job.result()]
        billed = job.total_bytes_billed or 0
        with (OUT_DIR / f"{f.stem}.csv").open("w", newline="") as fh:
            if rows:
                writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
                writer.writeheader()
                for r in rows:
                    writer.writerow({k: json.dumps(to_jsonable(v)) if isinstance(v, (list, tuple)) else to_jsonable(v)
                                     for k, v in r.items()})
        key = f.stem.split("_")[0]
        verdicts = JUDGES[key](rows)
        summary[f.stem] = {"scope": scope, "bytes_billed": billed, "criteria": [
            {"criterion": c, "value": v, "passed": p, "severity": s} for c, v, p, s in verdicts]}
        print(f"\n== {f.stem} (scope {scope}, billed {billed / 1e9:.3f} GB)")
        for c, v, p, s in verdicts:
            mark = "INFO" if p is None else ("PASS" if p else f"FAIL[{s}]")
            print(f"  {mark:22s} {c}: {v}")
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    fails = [(k, c["criterion"], c["severity"]) for k, s in summary.items() for c in s["criteria"] if c["passed"] is False]
    print(f"\n{len(fails)} failed criteria; blocking: {sum(1 for f in fails if f[2] == 'blocking')}")


if __name__ == "__main__":
    main()
