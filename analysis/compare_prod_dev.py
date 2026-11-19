"""Report Comparison A on prod next to dev, and flag rows whose sign changed or whose size moved by more
than 25% relative (prod estimate / dev estimate - 1). Reporting only: nothing here feeds the analysis.

Reads exports/comparison_a_prod.csv and analysis/output_dev/comparison_a_dev.csv. Because it contains
dev (provisional) numbers, the output stays in the git-ignored analysis/output_dev/ and never reaches
exports/. Dev used provisional 5%-sample bucket edges and thresholds; prod uses the frozen full-data
seeds (D55), so threshold-based metrics can move for that reason alone.
Usage: uv run python analysis/compare_prod_dev.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
KEYS = ["analysis", "metric", "variant", "weighting"]
COLS = ["estimate", "ci_low", "ci_high", "relative", "reg_p", "bootstrap_and_regression_agree"]
SIZE_LIMIT = 0.25


def main() -> None:
    prod = pd.read_csv(REPO_ROOT / "exports/comparison_a_prod.csv")[KEYS + COLS + ["n_users", "n_units"]]
    dev = pd.read_csv(REPO_ROOT / "analysis/output_dev/comparison_a_dev.csv")[KEYS + COLS]
    m = dev.merge(prod, on=KEYS, how="outer", suffixes=("_dev", "_prod"), indicator=True)
    unmatched = m[m["_merge"] != "both"]
    if len(unmatched):
        print("rows present in only one run:\n", unmatched[KEYS + ["_merge"]].to_string(index=False))
    m = m[m["_merge"] == "both"].drop(columns="_merge")
    m["sign_changed"] = np.sign(m.estimate_dev) != np.sign(m.estimate_prod)
    m["size_change"] = m.estimate_prod / m.estimate_dev - 1
    m["flag"] = m.sign_changed | (m.size_change.abs() > SIZE_LIMIT)
    m["agreement_changed"] = (m.bootstrap_and_regression_agree_dev
                              != m.bootstrap_and_regression_agree_prod)
    out = REPO_ROOT / "analysis/output_dev/comparison_a_prod_vs_dev.csv"
    m.to_csv(out, index=False)
    print(f"wrote {out.relative_to(REPO_ROOT)}: {len(m)} rows, {int(m.flag.sum())} flagged "
          f"({int(m.sign_changed.sum())} sign changes), {int(m.agreement_changed.sum())} agreement changes")
    show = m[KEYS + ["estimate_dev", "ci_low_dev", "ci_high_dev", "bootstrap_and_regression_agree_dev",
                     "estimate_prod", "ci_low_prod", "ci_high_prod", "bootstrap_and_regression_agree_prod",
                     "size_change", "sign_changed", "flag"]]
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(show.to_string(index=False, float_format=lambda x: f"{x:.5g}"))


if __name__ == "__main__":
    main()
