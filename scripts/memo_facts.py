"""Numbers for docs/memo.md that are not written out in findings.md (D61). Standard library only.

Reads committed exports and writes exports/memo/memo_facts.csv: one row per fact with the raw value, the
text the memo shows, and its source. scripts/check_memo.py then finds every memo number in findings.md
or in this export. Also checks the evidence tags the memo uses, so a tag appears only where it is true.

Usage: python scripts/memo_facts.py            # write exports/memo/memo_facts.csv
       python scripts/memo_facts.py --check    # fail if the committed file is stale
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "exports" / "memo" / "memo_facts.csv"
TOP_SHARE = 0.01388  # highest observed share of tab-1 exposures that are random (D48)


def rows(path: str) -> list[dict]:
    with (REPO_ROOT / path).open(newline="") as f:
        return list(csv.DictReader(f))


def pp(x: float, digits: int = 1) -> str:
    v = x * 100
    return f"{'−' if v < 0 else '+' if v > 0 else ''}{abs(v):.{digits}f}"


def interval(est: float, lo: float, hi: float, digits: int) -> str:
    return f"{pp(est, digits)} pp [{pp(lo, digits)}, {pp(hi, digits)}]"


def build() -> list[dict]:
    facts: list[dict] = []

    def add(name: str, value, display: str, source: str) -> None:
        facts.append({"name": name, "value": value, "display": display, "source": source})

    a = rows("exports/comparison_a_prod.csv")
    main = {r["metric"]: r for r in a if r["analysis"] == "A_request" and r["variant"] == "main" and r["weighting"] == "equal_user"}
    ev = main["effective_view"]

    # Feed-level effective-view change at the top observed share: share x the random-minus-recommended
    # difference (D48's linear rule), absolute and relative to the feed's (recommended) rate.
    feed_abs = TOP_SHARE * float(ev["estimate"])
    feed_rel = TOP_SHARE * float(ev["relative"])
    add("feed_effective_view_change_pp", feed_abs, f"{pp(feed_abs, 2).lstrip('−+')} pp", "comparison_a_prod.csv x 1.388%")
    add("feed_effective_view_change_relative", feed_rel, f"{abs(feed_rel) * 100:.2f}%", "comparison_a_prod.csv x 1.388%")

    # Robustness table (effective view and hate): main, AD pool excluded, top 0.1% user-days excluded,
    # within user. Tag "holds across robustness variants" only if every variant agrees in sign and methods.
    variants = [("A_request", "main", "main"), ("A_request", "ad_pool_excluded", "excl_ad_pool"),
                ("A_request", "top_user_day_excluded", "excl_top_user_days"), ("A_within_user", "main", "within_user")]
    for metric, digits in (("effective_view", 1), ("hate", 3)):
        signs, agrees = set(), []
        for analysis, variant, tag in variants:
            r = next(x for x in a if x["analysis"] == analysis and x["variant"] == variant
                     and x["weighting"] == "equal_user" and x["metric"] == metric)
            est, lo, hi = float(r["estimate"]), float(r["ci_low"]), float(r["ci_high"])
            add(f"robust_{metric}_{tag}", est, interval(est, lo, hi, digits), f"comparison_a_prod.csv {analysis}/{variant}")
            signs.add((lo > 0) - (hi < 0))
            agrees.append(r["bootstrap_and_regression_agree"] == "True")
        holds = len(signs) == 1 and 0 not in signs and all(agrees)
        add(f"robust_{metric}_holds", holds, "yes" if holds else "no", "comparison_a_prod.csv variants")

    # Targeting share across C's variants (tag check for the targeting finding).
    c = rows("exports/comparison_c_prod.csv")
    shares, c_agree = [], []
    for v in ("main", "ad_pool_excluded", "top_user_day_excluded"):
        t = {r["term"]: r for r in c if r["metric"] == "effective_view" and r["variant"] == v}
        shares.append(float(t["targeting"]["estimate"]) / float(t["total"]["estimate"]))
        c_agree += [t[k]["bootstrap_and_regression_agree"] == "True" for k in ("total", "content", "targeting")]
    holds_c = min(shares) > 0.9 and all(c_agree)
    add("targeting_share_holds", holds_c, "yes" if holds_c else "no", "comparison_c_prod.csv variants")
    add("targeting_share_main_methods_agree", all(c_agree[:3]), "yes" if all(c_agree[:3]) else "no", "comparison_c_prod.csv")

    # Methods agree for the evidence tags.
    add("a_all_metrics_agree", all(r["bootstrap_and_regression_agree"] == "True" for r in main.values()), "yes", "comparison_a_prod.csv")
    add("hate_methods_agree", main["hate"]["bootstrap_and_regression_agree"] == "True", "yes", "comparison_a_prod.csv")
    seg = rows("exports/segments_prod.csv")
    seg_ev_agree = all(r["effect_agree"] == "True" for r in seg if r["metric"] == "effective_view")
    add("segments_effective_view_agree", seg_ev_agree, "yes" if seg_ev_agree else "no", "segments_prod.csv")

    # Data quality.
    tab = rows("exports/health/hc07_random_by_tab.csv")
    tab1 = next(float(r["share_of_random"]) for r in tab if r["tab"] == "1")
    add("random_rows_on_tab1", tab1, f"{tab1 * 100:.1f}%", "health/hc07_random_by_tab.csv")
    md = {r["is_rand"]: float(r["missing_rate"]) for r in rows("exports/missing_duration_by_arm_prod.csv")}
    add("missing_duration_recommended", md["0"], f"{md['0'] * 100:.2f}%", "missing_duration_by_arm_prod.csv")
    add("missing_duration_random", md["1"], f"{md['1'] * 100:.2f}%", "missing_duration_by_arm_prod.csv")
    reg = rows("exports/health/hc01b_sample_ratio_tab1_regime.csv")
    for regime in ("low", "high"):
        cells = [r for r in reg if r["regime"] == regime and r["dimension"] == "activity_tercile"]
        share = sum(float(r["n_random"]) for r in cells) / sum(float(r["n_exposures"]) for r in cells)
        add(f"insertion_rate_{regime}", share, f"{share * 100:.3f}%", "health/hc01b_sample_ratio_tab1_regime.csv")

    # Build scale for the README, from the dashboard's build_facts (headline.json), the same numbers as
    # page 1's "How this was built".
    import json
    hb = json.loads((REPO_ROOT / "exports" / "dashboard" / "headline.json").read_text(encoding="utf-8"))["tables"]["build_facts"]
    bf = dict(zip(hb["columns"], hb["rows"][0]))
    add("build_raw_log_rows", bf["raw_log_rows"], f"{bf['raw_log_rows'] / 1e6:.1f} million", "dashboard/headline.json build_facts")
    add("build_users_in_dataset", bf["n_users_dataset"], f"{bf['n_users_dataset']:,}", "dashboard/headline.json build_facts")
    add("build_videos", bf["n_videos"], f"{bf['n_videos'] / 1e6:.1f} million", "dashboard/headline.json build_facts")
    add("build_gb_scanned", bf["bytes_billed_total"], f"{round(bf['bytes_billed_total'] / 1e9)} GB", "dashboard/headline.json build_facts")
    add("build_dbt_models", bf["n_models"], str(bf["n_models"]), "dashboard/headline.json build_facts")
    add("build_dbt_tests", bf["n_tests"], str(bf["n_tests"]), "dashboard/headline.json build_facts")

    # Power for the next experiment, two tiers (scripts/power_next_experiment.py).
    pw = rows("exports/memo/power_next_experiment.csv")[0]
    num = lambda k: float(pw[k])
    add("power_slot_users_per_arm", int(pw["slot_users_per_arm"]), f"{int(pw['slot_users_per_arm']):,}", "memo/power_next_experiment.csv")
    add("power_slot_delta", num("slot_delta"), f"{num('slot_delta') * 100:.0f} pp", "memo/power_next_experiment.csv")
    add("power_feed_users_per_arm", int(pw["feed_users_per_arm"]), f"{int(pw['feed_users_per_arm']):,}", "memo/power_next_experiment.csv")
    add("power_feed_users_total", int(pw["feed_users_total_four_arms"]), f"{int(pw['feed_users_total_four_arms']):,}", "memo/power_next_experiment.csv")
    add("power_feed_delta", num("feed_delta"), f"{num('feed_delta') * 100:.1f} pp", "memo/power_next_experiment.csv")
    add("power_feed_sd", num("feed_ev_sd"), f"{num('feed_ev_sd') * 100:.1f} pp", "memo/power_next_experiment.csv")
    add("power_hate_mde_pp", num("hate_mde_at_feed_n"), f"{num('hate_mde_at_feed_n') * 100:.4f} pp", "memo/power_next_experiment.csv")
    add("power_hate_mde_relative", num("hate_mde_at_feed_n") / num("hate_mean"), f"{num('hate_mde_at_feed_n') / num('hate_mean') * 100:.0f}%", "memo/power_next_experiment.csv")
    add("power_hate_limit_pp", num("hate_limit_abs"), f"{num('hate_limit_abs') * 100:.4f} pp", "memo/power_next_experiment.csv")
    add("power_hate_users_for_limit", int(pw["hate_users_per_arm_for_limit"]), f"{int(pw['hate_users_per_arm_for_limit']) / 1e6:.1f} million", "memo/power_next_experiment.csv")
    add("power_hate_needs_more_users", pw["hate_needs_more_users"] == "True", "yes" if pw["hate_needs_more_users"] == "True" else "no", "memo/power_next_experiment.csv")
    return facts


def render(facts: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["name", "value", "display", "source"], lineterminator="\n")
    w.writeheader()
    w.writerows(facts)
    return buf.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = render(build())
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("FAIL exports/memo/memo_facts.csv is stale; rerun scripts/memo_facts.py", file=sys.stderr)
            return 1
        print("ok: memo_facts.csv is current")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
