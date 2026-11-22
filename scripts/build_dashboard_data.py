"""Build the dashboard's data files from committed exports (D61). Standard library only; no BigQuery.

Reads exports/*.csv and two seeds, and writes one JSON file per dashboard page to exports/dashboard/.
Rows are copied as they are (a few rows dropped, listed below); nothing is recomputed here, so every
number on the dashboard traces to a committed export. Each table is stored as columns plus one row per
line, with the source file's SHA-256 so a stale build is caught.

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


def read_table(path: str, keep, key: list[str]) -> tuple[dict, dict]:
    raw = (REPO_ROOT / path).read_bytes()
    reader = csv.DictReader(raw.decode("utf-8").splitlines())
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


def render(page: str) -> str:
    """Stable text: one table row per line, so diffs show exactly which rows changed."""
    sources, tables = {}, {}
    for name, (path, keep, key) in PAGES[page].items():
        tables[name], sources[name] = read_table(path, keep, key)
    lines = ["{", f' "page": {json.dumps(page)},', f' "sources": {json.dumps(sources, ensure_ascii=False)},',
             ' "tables": {']
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

    b = records(texts["budget"], "budget")
    if len(b) != 45 or not any(r["dimension"] == "overall" for r in b):
        errors.append(f"budget: expected 45 rows including overall, found {len(b)}")
    seg_rows = {(r["dimension"], r["segment"]) for r in b if r["dimension"] != "overall"}
    if seg_rows != finals:
        errors.append("budget: segment rows differ from the merge map's final segments")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="compare with the committed files; write nothing")
    args = parser.parse_args()
    texts = {page: render(page) for page in PAGES}
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
