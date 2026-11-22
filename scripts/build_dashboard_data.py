"""Build the dashboard's data files from committed exports (D61). Standard library only; no BigQuery.

Reads exports/*.csv and two seeds, and writes one JSON file per dashboard page to exports/dashboard/.
Source rows are copied as they are (a few rows dropped, listed below), with the source file's SHA-256
so a stale build is caught. The few numbers the pages show that are not a column in an export (random
rates, the waterfall's random rate, shares and counts) are derived here, in DERIVED below, so the
browser only formats numbers and never computes them. Each table is stored as columns plus one row per
line.

Usage:
  python scripts/build_dashboard_data.py          # write exports/dashboard/*.json
  python scripts/build_dashboard_data.py --check  # fail if the committed JSON is stale or a check fails
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "exports" / "dashboard"


def keep_all(row: dict) -> bool:
    return True


def not_session_exit(row: dict) -> bool:
    # Session exit is not identifiable from these logs (D53); it never reaches the dashboard.
    return not row["analysis"].startswith("A_session_exit")


# page -> table name -> (source path relative to the repo, row filter, key columns that must be unique)
PAGES: dict[str, dict[str, tuple[str, object, list[str]]]] = {
    "headline": {
        "comparison_a": ("exports/comparison_a_prod.csv", not_session_exit,
                         ["analysis", "metric", "variant", "weighting"]),
        "missing_duration": ("exports/missing_duration_by_arm_prod.csv", keep_all, ["is_rand"]),
        "load_tables": ("docs/load_manifest.md", keep_all, ["table"]),
        "dbt_nodes": ("exports/build/dbt_nodes.csv", keep_all, ["resource_type", "name"]),
        "bytes_billed": ("exports/build/bytes_billed_by_month.csv", keep_all, ["month_pt"]),
    },
    "decomposition": {
        "comparison_c": ("exports/comparison_c_prod.csv", keep_all, ["metric", "variant", "term"]),
        "comparison_b": ("exports/comparison_b_prod.csv", keep_all, ["metric", "variant"]),
        "bridge_b_c": ("exports/bridge_b_c_prod.csv", keep_all, ["metric"]),
        "comparison_c_vs_a": ("exports/comparison_c_vs_a_prod.csv", keep_all, ["metric"]),
        "comparison_c_sample": ("exports/comparison_c_sample_prod.csv", keep_all, ["group"]),
        "pool_attributes": ("exports/health/hc02b_pool_attributes.csv", keep_all, ["video_set"]),
    },
    "segments": {
        "segments": ("exports/segments_prod.csv", keep_all, ["dimension", "segment", "metric"]),
        "merge_map": ("dbt/seeds/segment_merge_map.csv", keep_all, ["dimension", "segment"]),
        "category_labels": ("dbt/seeds/category_labels.csv", keep_all, ["category_segment"]),
    },
    "budget": {
        "budget": ("exports/exploration_budget_prod.csv", keep_all, ["dimension", "segment"]),
        "category_labels": ("dbt/seeds/category_labels.csv", keep_all, ["category_segment"]),
    },
}

INT_RE = re.compile(r"^-?\d+$")


def is_number(s: str) -> bool:
    try:
        float(s)
    except ValueError:
        return False
    return s.strip().lower() not in ("nan", "inf", "-inf", "infinity", "-infinity")


def column_type(values: list[str]) -> str:
    """One type per column: bool, int, float, or str. Empty cells are null and do not set the type."""
    present = [v for v in values if v != ""]
    if present and all(v in ("True", "False") for v in present):
        return "bool"
    if present and all(INT_RE.match(v) for v in present):
        return "int"
    if present and all(is_number(v) for v in present):
        return "float"
    return "str"


def convert(value: str, kind: str):
    if value == "":
        return None
    if kind == "bool":
        return value == "True"
    if kind == "int":
        return int(value)
    if kind == "float":
        return float(value)
    return value


def load_manifest_csv(text: str) -> list[str]:
    """The 'BigQuery tables' table of docs/load_manifest.md, as CSV lines (counts only)."""
    section = text.split("## BigQuery tables", 1)[1].split("\n## ", 1)[0]
    out = ["table,parquet_rows,bigquery_rows,event_dates"]
    for line in section.splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[1].replace(",", "").isdigit():
            out.append(",".join([cells[0], cells[1].replace(",", ""), cells[2].replace(",", ""), cells[3]]))
    return out


def read_table(path: str, keep, key: list[str]) -> tuple[dict, dict]:
    raw = (REPO_ROOT / path).read_bytes()
    lines = raw.decode("utf-8").splitlines()
    if path.endswith(".md"):
        lines = load_manifest_csv(raw.decode("utf-8"))
    reader = csv.DictReader(lines)
    columns = list(reader.fieldnames or [])
    rows = [r for r in reader if keep(r)]
    types = {c: column_type([r[c] for r in rows]) for c in columns}
    table = {"columns": columns, "types": [types[c] for c in columns],
             "rows": [[convert(r[c], types[c]) for c in columns] for r in rows]}
    seen = set()
    for r in rows:
        k = tuple(r[c] for c in key)
        if k in seen:
            raise SystemExit(f"{path}: duplicate key {dict(zip(key, k))}")
        seen.add(k)
    source = {"path": path, "sha256": hashlib.sha256(raw).hexdigest(), "rows_kept": len(rows)}
    return table, source


def value_type(values: list) -> str:
    present = [v for v in values if v is not None]
    if present and all(isinstance(v, bool) for v in present):
        return "bool"
    if present and all(isinstance(v, int) and not isinstance(v, bool) for v in present):
        return "int"
    if present and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in present):
        return "float"
    return "str"


def as_table(columns: list[str], rows: list[list]) -> dict:
    types = [value_type([r[i] for r in rows]) for i in range(len(columns))]
    return {"columns": columns, "types": types, "rows": rows}


def recs(table: dict) -> list[dict]:
    return [dict(zip(table["columns"], r)) for r in table["rows"]]


A_METRICS = ["effective_view", "naive_completion", "watch_time_ms", "like_", "comment_", "forward_",
             "profile_enter", "new_author_follow", "new_category_effective_view", "hate", "fast_skip"]


def a_main(src: dict) -> dict[str, dict]:
    rows = [r for r in recs(src["comparison_a"])
            if r["analysis"] == "A_request" and r["variant"] == "main" and r["weighting"] == "equal_user"]
    return {r["metric"]: r for r in rows}


def c_main(src: dict, metric: str) -> dict[str, dict]:
    return {r["term"]: r for r in recs(src["comparison_c"]) if r["variant"] == "main" and r["metric"] == metric}


def derive_headline(src: dict) -> dict:
    a = a_main(src)
    score = []
    for m in A_METRICS:
        r = a[m]
        base, est, lo, hi = r["baseline_rec"], r["estimate"], r["ci_low"], r["ci_high"]
        # Random-arm level = recommended level + random-minus-recommended difference (same weighting).
        # Relative interval = absolute interval / recommended rate (baseline treated as fixed, as in D59).
        score.append([m, base, base + est, est, lo, hi, r["relative"], lo / base, hi / base,
                      r["bootstrap_and_regression_agree"]])
    c = c_main(src, "effective_view")
    rec, content, targeting = c["total"]["baseline_rec_all"], c["content"]["estimate"], c["targeting"]["estimate"]
    shares = [r["recommended_share"] for r in recs(src["budget"]) if r["recommended_share"] is not None]
    ev = a["effective_view"]
    loads = {r["table"]: r for r in recs(src["load_tables"])}
    nodes = recs(src["dbt_nodes"])
    models = [n for n in nodes if n["resource_type"] == "model"]
    billed = recs(src["bytes_billed"])
    build = [[
        sum(loads[t]["bigquery_rows"] for t in ("log_random_treat", "log_standard_pre", "log_standard_treat")),
        loads["user_features"]["bigquery_rows"], loads["video_features_basic"]["bigquery_rows"],
        sum(r["bytes_billed"] for r in billed), max(r["snapshot_date"] for r in billed),
        len(models), *(sum(n["layer"] == layer for n in models) for layer in ("staging", "intermediate", "marts")),
        sum(n["resource_type"] == "test" for n in nodes), sum(n["resource_type"] == "seed" for n in nodes),
    ]]
    return {
        "scorecard": (as_table(["metric", "recommended_rate", "random_rate", "estimate", "ci_low", "ci_high",
                                "relative", "relative_ci_low", "relative_ci_high", "methods_agree"], score),
                      ["comparison_a"]),
        "waterfall": (as_table(["recommended_rate", "content_gap", "targeting_gap", "random_rate", "total_gap",
                                "targeting_share", "n_users", "a_gap"],
                               [[rec, content, targeting, rec - content - targeting, c["total"]["estimate"],
                                 targeting / c["total"]["estimate"], c["total"]["n_users"], -ev["estimate"]]]),
                      ["comparison_c", "comparison_a"]),
        "headline_facts": (as_table(["n_users", "n_random_requests", "n_metrics", "all_methods_agree", "top_share"],
                                    [[ev["n_users"], ev["n_units"], len(score),
                                      all(r[-1] is True for r in score), max(shares)]]),
                           ["comparison_a", "budget"]),
        "build_facts": (as_table(["raw_log_rows", "n_users_dataset", "n_videos", "bytes_billed_total",
                                  "bytes_snapshot_date", "n_models", "n_models_staging", "n_models_intermediate",
                                  "n_models_marts", "n_tests", "n_seeds"], build),
                        ["load_tables", "dbt_nodes", "bytes_billed"]),
    }


def derive_decomposition(src: dict) -> dict:
    c = c_main(src, "effective_view")
    total, content, targeting = (c[k]["estimate"] for k in ("total", "content", "targeting"))
    return {"decomposition_facts": (as_table(
        ["total_gap", "content_gap", "targeting_gap", "targeting_share", "effective_view_methods_agree"],
        [[total, content, targeting, targeting / total,
          all(c[k]["bootstrap_and_regression_agree"] is True for k in ("total", "content", "targeting"))]]),
        ["comparison_c"])}


def derive_segments(src: dict) -> dict:
    labels = {r["category_segment"]: r["label_en"] for r in recs(src["category_labels"])}
    ev = [r for r in recs(src["segments"]) if r["metric"] == "effective_view"]
    cats = [r for r in ev if r["dimension"] == "category_segment" and r["interpretable"] is True]
    worst = min(cats, key=lambda r: r["estimate"])
    best = max(cats, key=lambda r: r["estimate"])
    return {"segments_facts": (as_table(
        ["worst_category", "worst_label", "worst_estimate", "best_category", "best_label", "best_estimate",
         "effective_view_methods_agree_all"],
        [[worst["segment"], labels[worst["segment"]], worst["estimate"], best["segment"], labels[best["segment"]],
          best["estimate"], all(r["effect_agree"] is True for r in ev)]]),
        ["segments", "category_labels"])}


COST_METRICS = ["effective_view", "new_author_follow", "new_category_effective_view"]


def derive_budget(src: dict) -> dict:
    segs = [r for r in recs(src["budget"]) if r["dimension"] != "overall"]
    clear = [r for r in segs if r["binding_guardrail"] == "none in range"]
    # Per-impression A estimates behind the budget's costs (exploration_budget.py: cost per 1,000 =
    # share x estimate x 1,000), so the simulator can show costs at any share in the range.
    seg_est = {(r["dimension"], r["segment"], r["metric"]): r["estimate"] for r in recs(src["segments"])}
    a = a_main(src)
    costs = []
    for r in recs(src["budget"]):
        key = (r["dimension"], r["segment"])
        est = [a[m]["estimate"] if key == ("overall", "all") else seg_est[(*key, m)] for m in COST_METRICS]
        costs.append([*key, *est])
    return {
        "budget_facts": (as_table(["n_segments", "n_no_guardrail_crossed"], [[len(segs), len(clear)]]), ["budget"]),
        "budget_estimates": (as_table(["dimension", "segment", *[f"{m}_estimate" for m in COST_METRICS]], costs),
                             ["budget", "segments", "comparison_a"]),
    }


DERIVED = {"headline": derive_headline, "decomposition": derive_decomposition,
           "segments": derive_segments, "budget": derive_budget}


def read_all() -> dict[str, tuple[dict, dict]]:
    out = {}
    for page in PAGES.values():
        for name, (path, keep, key) in page.items():
            out[name] = read_table(path, keep, key)
    return out


def render(page: str, all_src: dict[str, tuple[dict, dict]]) -> str:
    """Stable text: one table row per line, so diffs show exactly which rows changed."""
    sources = {name: all_src[name][1] for name in PAGES[page]}
    tables = {name: all_src[name][0] for name in PAGES[page]}
    derived_from = {}
    for name, (table, used) in DERIVED[page]({n: s[0] for n, s in all_src.items()}).items():
        tables[name] = table
        derived_from[name] = {"script": "scripts/build_dashboard_data.py", "from": [all_src[u][1]["path"] for u in used]}
    lines = ["{", f' "page": {json.dumps(page)},', f' "sources": {json.dumps(sources, ensure_ascii=False)},',
             f' "derived": {json.dumps(derived_from, ensure_ascii=False)},', ' "tables": {']
    for i, (name, t) in enumerate(tables.items()):
        lines.append(f'  {json.dumps(name)}: {{"columns": {json.dumps(t["columns"])}, '
                     f'"types": {json.dumps(t["types"])}, "rows": [')
        for j, row in enumerate(t["rows"]):
            comma = "," if j < len(t["rows"]) - 1 else ""
            lines.append("   " + json.dumps(row, ensure_ascii=False, allow_nan=False) + comma)
        lines.append("  ]}" + ("," if i < len(tables) - 1 else ""))
    lines += [" }", "}"]
    return "\n".join(lines) + "\n"


def records(page_text: str, table: str) -> list[dict]:
    t = json.loads(page_text)["tables"][table]
    return [dict(zip(t["columns"], r)) for r in t["rows"]]


def content_checks(texts: dict[str, str]) -> list[str]:
    """Assumptions the pages rely on. Each failure is a message; an empty list means all pass."""
    errors = []
    a = records(texts["headline"], "comparison_a")
    main = [r for r in a if r["analysis"] == "A_request" and r["variant"] == "main" and r["weighting"] == "equal_user"]
    if len(main) != 11:
        errors.append(f"headline: expected 11 main equal-user A rows, found {len(main)}")
    if any(r["analysis"].startswith("A_session_exit") for r in a):
        errors.append("headline: session-exit rows must be dropped (D53)")
    for r in main:
        if not (r["ci_low"] <= r["estimate"] <= r["ci_high"]):
            errors.append(f"headline: {r['metric']} estimate outside its interval")

    c = records(texts["decomposition"], "comparison_c")
    for m in {r["metric"] for r in c if r["variant"] == "main"}:
        terms = {r["term"]: r["estimate"] for r in c if r["variant"] == "main" and r["metric"] == m}
        if abs(terms["total"] - terms["content"] - terms["targeting"]) > 1e-9 * max(1.0, abs(terms["total"])):
            errors.append(f"decomposition: C terms do not add up for {m}")

    seg = records(texts["segments"], "segments")
    mm = records(texts["segments"], "merge_map")
    labels = {r["category_segment"] for r in records(texts["segments"], "category_labels")}
    finals = {(r["dimension"], r["final_segment"]) for r in mm}
    shown = {(r["dimension"], r["segment"]) for r in seg}
    if shown != finals:
        errors.append(f"segments: segment rows differ from the merge map's final segments: {sorted(shown ^ finals)}")
    missing = {r["segment"] for r in mm if r["dimension"] == "category_segment"} - labels
    if missing:
        errors.append(f"segments: categories without a label: {sorted(missing)}")

    sc = records(texts["headline"], "scorecard")
    if [r["metric"] for r in sc] != A_METRICS:
        errors.append("headline: scorecard rows differ from the 11 A metrics")
    by_metric = {r["metric"]: r for r in main}
    for r in sc:
        src = by_metric[r["metric"]]
        if abs(r["random_rate"] - r["recommended_rate"] - src["estimate"]) > 1e-12:
            errors.append(f"headline: random rate for {r['metric']} is not recommended + difference")
        if not (r["relative_ci_low"] <= r["relative"] <= r["relative_ci_high"]):
            errors.append(f"headline: {r['metric']} relative estimate outside its relative interval")
        if r["metric"] != "watch_time_ms" and not (0 <= r["random_rate"] <= 1):
            errors.append(f"headline: random rate for {r['metric']} outside 0-1")
    (w,) = records(texts["headline"], "waterfall")
    if abs(w["recommended_rate"] - w["content_gap"] - w["targeting_gap"] - w["random_rate"]) > 1e-12:
        errors.append("headline: waterfall does not add up")
    if abs(w["recommended_rate"] - w["random_rate"] - w["total_gap"]) > 1e-9:
        errors.append("headline: waterfall total differs from C's total gap")
    (hf,) = records(texts["headline"], "headline_facts")
    if hf["top_share"] != 0.01388:
        errors.append(f"headline: top observed share is {hf['top_share']}, expected 0.01388 (D48)")

    for r in records(texts["headline"], "load_tables"):
        if r["parquet_rows"] != r["bigquery_rows"]:
            errors.append(f"build: {r['table']} row counts differ between parquet and BigQuery")
    (bf,) = records(texts["headline"], "build_facts")
    if bf["n_models"] != bf["n_models_staging"] + bf["n_models_intermediate"] + bf["n_models_marts"]:
        errors.append("build: dbt models are not all in staging, intermediate or marts")
    if not (bf["raw_log_rows"] > 0 and bf["n_tests"] > 0 and bf["bytes_billed_total"] > 0):
        errors.append("build: a build statistic is missing")

    b = records(texts["budget"], "budget")
    if len(b) != 45 or not any(r["dimension"] == "overall" for r in b):
        errors.append(f"budget: expected 45 rows including overall, found {len(b)}")
    est = {(r["dimension"], r["segment"]): r for r in records(texts["budget"], "budget_estimates")}
    for r in b:
        if r["recommended_share"] is None:
            continue
        for m in COST_METRICS:
            want = r[f"{m}_change_per_1000_impressions"]
            got = r["recommended_share"] * est[(r["dimension"], r["segment"])][f"{m}_estimate"] * 1000
            if abs(got - want) > 1e-9:
                errors.append(f"budget: {m} estimate for {r['dimension']}/{r['segment']} does not reproduce the cost")
    seg_rows = {(r["dimension"], r["segment"]) for r in b if r["dimension"] != "overall"}
    if seg_rows != finals:
        errors.append("budget: segment rows differ from the merge map's final segments")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="compare with the committed files; write nothing")
    args = parser.parse_args()
    all_src = read_all()
    texts = {page: render(page, all_src) for page in PAGES}
    errors = content_checks(texts)
    for page, text in texts.items():
        path = OUT_DIR / f"{page}.json"
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                errors.append(f"{path.relative_to(REPO_ROOT)} is stale; rerun scripts/build_dashboard_data.py")
        else:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(REPO_ROOT)} ({len(text.encode()) / 1024:.0f} KB)")
    for e in errors:
        print(f"FAIL {e}", file=sys.stderr)
    if not errors and args.check:
        print(f"ok: {len(texts)} files current, all content checks pass")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
