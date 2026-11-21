# Findings (working record)

Status: **prod (full data). Comparisons A, B and C complete;** segments and the exploration budget are
next. A comes from `exports/comparison_a_prod.csv` (2026-11-20), B from `exports/comparison_b_prod.csv`
and C from `exports/comparison_c*_prod.csv` (2026-11-21), each written by its script in `analysis/` with
`--target prod` and the frozen full-data bucket edges and thresholds (D55). Pre-registered plan: `docs/analysis_plan.md` (`prereg-v1`); deviations and
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

## Comparison B on prod: the same pool video, random vs recommended (2026-11-21)
5,591 pool videos with exposures in both arms (866,218 random and 203,562 recommended items). Per video,
random minus recommended, equal weight per video; video-clustered bootstrap with a user-clustered
bootstrap as robustness; video fixed-effects regression, SEs by video.

| Metric | Recommended (pool videos) | Random minus recommended [95% CI] | Relative |
| --- | ---: | --- | ---: |
| Effective view | 46.5% | −25.0 pp [−25.7, −24.2] | −54% |
| Naive completion | 11.9% | −8.2 pp [−8.7, −7.8] | −69% |
| Watch time | 22.2 s | −14.7 s [−15.4, −14.1] | −66% |
| Like | 2.03% | −1.53 pp [−1.72, −1.35] | −75% |
| Comment | 0.317% | −0.278 pp [−0.368, −0.205] | −88% |
| Forward | 0.087% | −0.054 pp [−0.080, −0.031] | −62% |
| Profile enter | 1.84% | −1.26 pp [−1.42, −1.10] | −68% |
| New-author follow | 0.105% | −0.079 pp [−0.118, −0.047] | −75% |
| New-category effective view | 1.28% | −0.42 pp [−0.57, −0.28] | −33% |
| Hate | 0.086% | +0.027 pp [−0.012, +0.060] | +31% |
| Fast skip | 38.5% | +23.4 pp [+22.7, +24.2] | +61% |

- The same video does much worse when shown at random than when recommended: holding content fixed,
  targeting is worth most of the gap. Every metric except hate agrees across both methods, both
  bootstraps and all sensitivity runs.
- **Hate in B: underpowered, not contradictory (D60).** Neither method finds a significant difference
  in any variant (regression p = 0.15 to 0.17). The 95% interval (−0.012 to +0.060 pp) includes both
  zero and A's +0.058 pp effect, and B's minimum detectable effect at 80% power is about 0.05 pp, close
  to A's effect: B has too few recommended pool exposures (203,562) to detect a hate effect of that
  size. It does not contradict A or C.

## Comparison C on prod: content vs targeting (2026-11-21)
Recommended minus random, within day (days weighted by each user's random items), equal user weight;
the three terms use the same user-days and add up exactly. 22,335 users, 72,287 user-days.

| Metric | Total gap | Content gap (rec all − rec pool) | Targeting gap (rec pool − random) | Content share |
| --- | --- | --- | --- | ---: |
| Effective view | 35.7 pp [35.4, 35.9] | 2.1 pp [1.7, 2.5] | 33.6 pp [33.2, 34.1] | 6% |
| Naive completion | 19.8 pp | 5.8 pp | 14.0 pp | 29% |
| Watch time | 15.8 s | −4.7 s | 20.6 s | n/a (opposite signs) |
| Like | 1.87 pp | 0.53 pp | 1.33 pp | 29% |
| Profile enter | 1.98 pp | 0.34 pp | 1.64 pp | 17% |
| New-author follow | 0.117 pp | 0.046 pp | 0.071 pp | 39% |
| New-category effective view | 0.76 pp | 0.08 pp (borderline, p = 0.046) | 0.68 pp | 11% |
| Fast skip (random higher) | −31.7 pp | −0.9 pp | −30.8 pp | 3% |
| Hate (random higher) | −0.070 pp | −0.018 pp (not significant) | −0.053 pp | n/a |
| Comment, forward | 0.31, 0.087 pp | not significant | 0.26, 0.075 pp | n/a |

- **Targeting, not content, drives the cost of a random slot.** For the primary metric 94% of the gap is
  targeting; the pool's content is only 2.1 pp below typical recommended content. Pool videos earn
  more watch time than typical recommended videos when recommended (content gap −4.7 s), while their
  completion is lower, because pool videos are longer: HC 2 found a median duration of 81 s for pool
  videos vs 34 s for standard-exposed videos (distinct videos, standard side from the dev sample;
  `docs/data_quality.md`, `exports/health/hc02b_pool_attributes.csv`). Longer videos accumulate more
  watch time per view but are completed less often (D60). The content share is largest for
  new-author follows (39%).
- Every total and targeting term agrees across both methods in every variant. Content gaps for comment,
  forward and hate are not significant, so they are not findings.
- **B and C's targeting gap differ by weighting.** B weights each pool video equally over all its
  exposures (−25.0 pp for effective view); C's targeting gap weights users and their days and
  compares a user's recommended pool items with that user's random items (33.6 pp). For hate the two
  disagree: C's targeting gap is significant (random higher by 0.053 pp) while B finds no significant
  difference; B is underpowered for hate (see above), so this is not a contradiction, but hate's
  targeting component rests on C alone.

### B vs C's targeting gap (D60 bridge)
In random-minus-recommended terms, main run (`exports/bridge_b_c_prod.csv`): B on all pool exposures,
then B's equal-video estimator on C's sample (pool exposures on C's kept user-days; 5,131 videos,
481,081 items), then C's targeting gap.

| Metric | B, all pool exposures | B on C's sample [95% CI] | C targeting | Sample part | Weighting part |
| --- | --- | --- | --- | ---: | ---: |
| Effective view | −25.0 pp | −25.8 pp [−26.6, −25.0] | −33.6 pp | −0.85 pp | −7.8 pp |
| Naive completion | −8.2 pp | −8.6 pp | −14.0 pp | −0.34 pp | −5.4 pp |
| Watch time | −14.7 s | −15.0 s | −20.6 s | −0.3 s | −5.5 s |
| Fast skip | +23.4 pp | +24.7 pp | +30.8 pp | +1.2 pp | +6.1 pp |
| Hate | +0.027 pp | +0.063 pp [+0.011, +0.100] | +0.053 pp | +0.036 pp | −0.010 pp |
| New-author follow | −0.079 pp | −0.072 pp | −0.071 pp | +0.007 pp | +0.001 pp |

- For the primary metric and the other watch-based metrics, the B vs C difference is almost all
  weighting: B weights each pool video equally, C weights users and their days. Who is in C's sample
  changes B by under 1 pp.
- For hate, the sample part dominates: on C's sample, B's own estimator finds a significant increase
  (+0.063 pp; both methods agree), in line with A and C. This supports reading B's full-sample hate
  result as underpowered rather than as no effect.
- For like and comment each part is under a fifth of B's gap, and for new-author follow both are near
  zero. Forward, a rare outcome, moves with both (+0.012 pp sample, −0.033 pp weighting, on a −0.054 pp
  B gap). New-category effective view moves with weighting like the watch-based metrics (−0.08
  pp sample, −0.18 pp weighting, on a −0.42 pp B gap).

### C's sample and the C vs A difference (D59 addendum)
- The same-day rule keeps 43.5% of random items (user-days with at least one recommended pool item).
  C's sample is 22,335 of 26,998 users with a random item. It leans toward more active users
  (pre-period activity tercile 1: 28.7% vs 32.7% of all users; tercile 3: 36.1% vs 33.0%) and users
  with more random items (median 23 vs 21 in the window).
- Effective view, in random-minus-recommended terms: A on all requests −34.6 pp; A on C's sample
  −34.8 pp (sample difference −0.14 pp); C's total gap −35.7 pp (weighting difference −0.91 pp). For
  the primary metric, both differences are small; most of the gap between A and C comes from weighting
  (same-request vs same-day comparison), not from who is in C's sample.
- For most secondary and discovery metrics the sample difference is as large as or larger than the
  weighting difference (for example naive completion +0.85 vs −0.74 pp, new-category effective view
  −0.21 vs −0.001 pp, new-author follow +0.045 vs +0.004 pp; for fast skip the weighting difference is
  larger, +0.74 vs +0.55 pp), so C's decomposition describes the more active users with recommended
  pool items on the same day, not all users.

## Hypotheses
- **H1 (cost): supported.** Random slots cost on every identifiable engagement metric, and raise both
  identifiable guardrails (hate, fast skip).
- **H2 (hidden session cost): not testable.** Session exit is not identifiable from these logs (D53).
- **H3 (discovery benefit): not supported.** Per impression, random slots produce fewer new-author
  follows (−85%) and fewer new-category effective views (−31%) than recommended slots in the same
  request.
- **H4 (heterogeneity):** not yet tested (segments run next, with the committed merge map 9929e2c).

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
