"""Apply the D52 decision rules to exports/diagnostics/d02_session_position_truncation.csv.

Rules (docs/decisions.md D52, fixed before the query ran):
  position explains the gap   if |first-request insertion rate / middle-request rate - 1| > 5%
  truncation explains the gap if final requests show >= 5% fewer tab-1 items than other requests AND,
                              among non-final requests, the insertion rate at the modal item count is
                              >= 5% higher than in smaller requests
Usage: uv run python analysis/diagnostics/d02_evaluate.py
"""

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
d = pd.read_csv(REPO_ROOT / "exports/diagnostics/d02_session_position_truncation.csv")

pos = d.groupby("position")[["n_requests", "n_random_requests"]].sum()
pos["insertion_rate"] = pos["n_random_requests"] / pos["n_requests"]
mean_items = d.assign(w=d.n_items_capped * d.n_requests).groupby("position").apply(
    lambda g: g.w.sum() / g.n_requests.sum(), include_groups=False)
pos["mean_tab1_items"] = mean_items
print("By session position (items capped at 12):")
print(pos.to_string(float_format=lambda x: f"{x:.4f}"))

first, middle = pos.loc["a0_first", "insertion_rate"], pos.loc["a1_middle", "insertion_rate"]
position_dev = first / middle - 1
position_fires = abs(position_dev) > 0.05

final = d[d.position == "d_last"]
other = d[d.position != "d_last"]
items_final = (final.n_items_capped * final.n_requests).sum() / final.n_requests.sum()
items_other = (other.n_items_capped * other.n_requests).sum() / other.n_requests.sum()
items_gap = items_final / items_other - 1

by_items = other.groupby("n_items_capped")[["n_requests", "n_random_requests"]].sum()
by_items["insertion_rate"] = by_items.n_random_requests / by_items.n_requests
modal = int(by_items.n_requests.idxmax())
smaller = by_items[by_items.index < modal]
rate_modal = by_items.loc[modal, "insertion_rate"]
rate_smaller = smaller.n_random_requests.sum() / smaller.n_requests.sum()
rate_gap = rate_modal / rate_smaller - 1
truncation_fires = items_gap <= -0.05 and rate_gap >= 0.05

# Items per request by whether the request has a random item (all positions).
rnd_items = d.assign(nr=d.n_requests - d.n_random_requests)
with_random = (d.n_items_capped * d.n_random_requests).sum() / d.n_random_requests.sum()
without_random = (rnd_items.n_items_capped * rnd_items.nr).sum() / rnd_items.nr.sum()

print("\nInsertion rate by tab-1 items per request (non-final requests):")
print(by_items.to_string(float_format=lambda x: f"{x:.4f}"))
print(f"\nmean tab-1 items: requests with a random item {with_random:.2f}, without {without_random:.2f}")
print(f"\nRule 1 (position): first {first:.4%} vs middle {middle:.4%} -> {position_dev:+.1%} -> "
      f"{'FIRES' if position_fires else 'does not fire'}")
print(f"Rule 2 (truncation): final-request items {items_final:.2f} vs other {items_other:.2f} ({items_gap:+.1%}); "
      f"insertion at modal size {modal} {rate_modal:.4%} vs smaller {rate_smaller:.4%} ({rate_gap:+.1%}) -> "
      f"{'FIRES' if truncation_fires else 'does not fire'}")
print(f"\nSession exit identifiable from these logs: {'NO' if (position_fires or truncation_fires) else 'not ruled out by D52'}")
