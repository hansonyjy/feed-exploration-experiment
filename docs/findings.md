# Findings (working record)

Status: **prod (full data), Comparison A complete.** Comparisons B and C, segments and the exploration
budget are Phase 2. Every number below comes from `exports/comparison_a_prod.csv`, written by
`analysis/comparison_a.py --target prod` on 2026-11-20 with the frozen full-data bucket edges and
thresholds (D55). Pre-registered plan: `docs/analysis_plan.md` (`prereg-v1`); deviations and
post-results decisions: `docs/decisions.md`.

## Comparison A on prod (2026-11-20)
Main run: random item minus the mean of the recommended items in the same feed request, tab 1,
2022-04-23 to 05-08, equal weight per user. 26,955 users, 1,081,088 random requests. 95% intervals from
the user-clustered bootstrap (2,000 resamples, seed 20261115); cross-check by OLS with request fixed
effects, SEs clustered by user (D49).

| Tier | Metric | Recommended rate | Random minus recommended [95% CI] | Relative | Methods agree |
| --- | --- | ---: | --- | ---: | --- |
| Primary | Effective view | 54.8% | −34.6 pp [−34.8, −34.5] | −63% | yes |
| Secondary | Naive completion | 23.4% | −19.9 pp [−20.1, −19.8] | −85% | yes |
| Secondary | Watch time per impression | 23.5 s | −16.4 s [−16.5, −16.2] | −70% | yes |
| Secondary | Like | 2.44% | −1.94 pp [−2.01, −1.88] | −80% | yes |
| Secondary | Comment | 0.354% | −0.323 pp [−0.343, −0.305] | −91% | yes |
| Secondary | Forward | 0.124% | −0.090 pp [−0.099, −0.081] | −73% | yes |
| Secondary | Profile enter | 2.61% | −2.07 pp [−2.13, −2.02] | −79% | yes |
| Discovery | New-author follow | 0.196% | −0.166 pp [−0.182, −0.150] | −85% | yes |
| Discovery | New-category effective view | 1.76% | −0.55 pp [−0.63, −0.48] | −31% | yes |
| Guardrail | Hate | 0.053% | +0.058 pp [+0.044, +0.073] | +110% | yes |
| Guardrail | Fast skip | 33.1% | +30.4 pp [+30.2, +30.6] | +92% | yes |
| Guardrail | Session exit | — | not identifiable (D53) | — | — |

- **Robustness:** every metric keeps its sign and significance in all variants: within-user
  comparison, population weighting, excluding the top 0.1% of user-days, excluding AD pool videos, and
  (for non-duration metrics) with missing-duration rows included. All 68 rows have bootstrap intervals
  that exclude zero and regression p < 1e-9, and the two methods agree on every row. The
  duration-bucket-controlled regression (a diagnostic, D49) has the same sign on every metric.
- **Missing duration (reported with every primary result, D23):** 7.81% of recommended and 3.11% of
  random tab-1 items lack a valid duration and are excluded from duration-based metrics in the main run.
- **Hate: a finding (D56).** Random slots roughly double the hate rate: +0.058 pp absolute, +110%
  relative. Hate is rare (0.053% of recommended impressions, about 1 in 1,900), so the absolute effect is
  small: about one extra hate per 1,700 random impressions. The dev label "inconclusive" was
  provisional; on prod the bootstrap and regression agree in sign and significance in all six variants,
  which meets the pre-registered headline rule.
- **Session exit: not identifiable from these logs (D52, D53).** Insertion depends on session position
  (first requests +23.4% vs middle), and final requests are truncated (3.07 vs 5.64 tab-1 items, with
  insertion rising steeply with items shown). The computed contrast (−5.0 pp) is not reported as an
  effect, and no direction is claimed.

## Hypotheses
- **H1 (cost): supported.** Random slots cost on every identifiable engagement metric, and raise both
  identifiable guardrails (hate, fast skip).
- **H2 (hidden session cost): not testable.** Session exit is not identifiable from these logs (D53).
- **H3 (discovery benefit): not supported.** Per impression, random slots produce fewer new-author
  follows (−85%) and fewer new-category effective views (−31%) than recommended slots in the same
  request.
- **H4 (heterogeneity):** not yet tested (Phase 2 segments).

## Exploration budget (D54, D56)
- The budget uses the item-level guardrails only; session-level impact is not identifiable from these
  logs, and the budget says so (D54). Otherwise computed exactly as in D48.
- D54 reported hate with its interval because it was inconclusive on dev. Hate is now a finding (D56);
  whether it constrains the budget as in D48 is an open question for the owner.

## Appendix: stability from dev to prod
Dev (5% hashed user sample, 1,237 users, run 2026-11-18 with provisional 5%-sample edges and thresholds)
against prod, compared with `analysis/compare_prod_dev.py` across all 68 rows (metric × variant):
- **No sign changes.** Every prod estimate lies inside its dev 95% interval.
- **14 rows moved by more than 25% relative** (forward: 6 rows; new-category effective view: 5; hate
  within user: 1; comment, population-weighted and within user: 2). These are low-count metrics, with
  base rates of 0.05% to 1.8%, where dev intervals were wide. New-category effective view also depends
  on the effective-view threshold, which moved from the provisional dev values to the frozen full-data
  seeds (D55). The primary metric moved by about 1%.
- **Agreement:** six rows where the methods disagreed on dev agree on prod (hate: 3; forward: 2;
  new-category effective view: 1). No row went the other way.
- Dev outputs stay git-ignored under `analysis/output_dev/`; dev numbers are never quoted as results.
