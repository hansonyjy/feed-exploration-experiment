# Findings (working record)

Status: **dev sample only (5% of users), provisional.** Nothing here is a headline until the prod run.
Dev estimates come from `analysis/comparison_a.py` (output git-ignored under `analysis/output_dev/`);
full-data diagnostics from `analysis/diagnostics/`. Pre-registered plan: `docs/analysis_plan.md`
(`prereg-v1`); deviations and post-results decisions: `docs/decisions.md`.

## Comparison A on dev (2026-11-18)
- All pre-registered item-level metrics show a cost for a random slot relative to recommended items in
  the same request, with the bootstrap and the request fixed-effects regression agreeing, except as
  noted below. Exact dev values are not quoted here because they are provisional.
- **Hate rate: inconclusive.** The main estimate is barely significant (regression p = 0.045), and the
  bootstrap and regression disagree in three of six variants (population-weighted, within-user, with
  missing-duration rows).
- **Session exit: not identifiable from these logs (D52, D53).** Insertion depends on session position
  (first requests +23.4% vs middle), and final requests are truncated (3.07 vs 5.64 tab-1 items, with
  insertion rising steeply with items shown). No direction is claimed.

## Hypotheses (dev, pending prod)
- **H1 (cost):** supported on dev for every identifiable metric except hate (inconclusive).
- **H2 (hidden session cost):** not supported on dev. Session exit is not identifiable (D53), so H2
  cannot be tested through session exit with these logs, on dev or on prod.
- **H3 (discovery benefit):** not supported on dev. Random slots produce fewer new-author follows and
  fewer new-category effective views than recommended slots in the same request.
- **H4 (heterogeneity):** not yet tested (segments come after the prod run).

## Open questions for the owner
- The D48 session-exit guardrail cannot constrain the exploration budget. Whether the budget proceeds
  with the item-level guardrails only must be decided and logged before the budget is computed.
