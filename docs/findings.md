# Findings (working record)

Status: **prod (full data). Comparisons A, B and C, segments and the exploration budget complete.** A comes from `exports/comparison_a_prod.csv` (2026-11-20), B from `exports/comparison_b_prod.csv`
C from `exports/comparison_c*_prod.csv` and `exports/bridge_b_c_prod.csv`, segments from
`exports/segments_prod.csv` and the budget from `exports/exploration_budget_prod.csv` (2026-11-21), each written by its script in `analysis/` with
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

## Segments on prod (2026-11-21)
Comparison A (main run, equal user weight) by merged segment (map 9929e2c; D39, D40, D58), five metrics.
Each segment's contrast is its effect minus the effect in the rest of its dimension; BH (q = 0.10) and
BY run per metric across all 44 contrasts, on regression and bootstrap p-values separately (D57, D59).
Contrasts within a dimension are negatively correlated (each segment is part of the others' rest), so
BY, valid under any dependence, is reported alongside. Merged category groups are power-based groupings
(D40) with no topical meaning and are not interpreted below; category names are translations of the
supplementary file's labels.

- **Every segment pays a large effective-view cost:** from −27.9 pp to −42.2 pp (vs −34.6 pp overall),
  with both methods agreeing in every segment. With over a million random requests, most contrasts are
  significant (BH findings out of 44: effective view 38, fast skip 31, new-category effective view 34,
  new-author follow 16, hate 11; BY confirms most, but only 6 of the 11 for hate), so size matters more
  than significance.
- **Content type varies most.** Effective-view cost by the random item's category: gaming −42.2 pp
  (−77%), anime −39.7 pp, music −38.3 pp, dance −36.5 pp, versus comedy −28.3 pp (−51%), film/TV/variety
  −30.8 pp, short drama −33.4 pp, food −33.0 pp. By duration: buckets 3-6 (about 10-58 s) cost −27.9 to
  −31.8 pp, buckets 7-10 (over about 58 s) −36.5 to −38.0 pp. Fast skip follows the same pattern
  (gaming +41.6 pp, film/TV/variety +21.9 pp).
- **User segments differ less, and the direction depends on the scale.** In absolute terms the most
  active pre-period tercile pays the least (−30.9 pp vs −37.0 pp for tercile 1 with no-pre-period users),
  but its recommended baseline is also much lower (44.6% vs 63.3%), so in relative terms it pays the most
  (−69% vs −58%). Tenure, follow-count and activity-group contrasts are within ±3 pp absolute.
- **New-category engagement (H3):** for pre-period terciles 2 and 3 and full-active users, random slots
  produce as many or slightly more new-category effective views than recommended slots (tercile 2:
  +0.044 pp, significant in both methods; tercile 3 and full-active: +0.013 and +0.005 pp, not
  significant), while for low-activity, new and low-follow users they produce far fewer (for example
  −4.1 pp for new-or-low/middle-active users, −2.7 pp for users following 0-10 accounts). Part of this
  is mechanical: users with little pre-period history have few categories with an effective view, so
  more of their recommended items count as new.
- **New-author follows:** lower for random slots in every segment (−73% to −96%); the absolute loss is
  largest for users with 500+ follows (−0.43 pp) and new or short-tenure users (−0.41 pp for 8-180 days).
- **Hate:** the increase is concentrated in a few segments. Dance random items raise hate by +0.25 pp
  (+382%; BH and BY finding); food, sports and comedy show no detectable increase (contrasts −0.04 to
  −0.06 pp, findings). Among user segments, full-active users and users with 730+ days of tenure show a
  smaller hate increase than the rest (contrasts −0.059 and −0.061 pp; BH and BY findings); the larger
  increases for newer, less active and low-follow users are BH-only findings or leads (for example
  users with 181-365 days of tenure, +0.149 pp, a lead), so they are not robust under BY.

## Exploration budget on prod (2026-11-21)
Binding guardrails: hate and fast skip, each limited to a 2% relative worsening of the feed; session
exit is not identifiable and is left out (D53, D54, D57). Share s interpolated only between 0.658% and
1.388% of tab-1 exposures; the baseline is the D48 recommended rate (user segments: within segment;
item segments: overall; D59). Hate changes are given in absolute pp of tab-1 impressions first, then
relative. Hate is rare (0.051% overall), so the 2% limit is about +0.0010 pp absolute, roughly one extra
hate per 100,000 tab-1 impressions (user segments: 2% of their own baseline).

**1.388% is the highest share observed in the logs, not an optimum.** The budget can only say that no
guardrail is crossed up to that share; what happens above it is unknown, and a higher share needs a new
test that runs it (no extrapolation).

### Actionable results
- **Overall: no guardrail binds up to 1.388%.** At 1.388%, hate rises +0.00081 pp [+0.00062, +0.00101]
  (+1.60% relative) and fast skip +0.42 pp (+1.32%), both under the limit. At 1.388%, the expected cost
  is 4.8 fewer effective views, 0.023 fewer new-author follows and 0.077 fewer new-category effective
  views per 1,000 tab-1 impressions.
- **Dance random items: the only robust hate binding.** Hate already exceeds the limit at the bottom of
  the observed range: at 0.658%, +0.0017 pp [+0.0012, +0.0022] (+3.3% relative [+2.3%, +4.3%]) against a
  limit of +0.0010 pp, so the binding share lies below 0.658% and the interval stays above the limit.
  Dance is the one segment where the data supports limiting exploration content.
- **Fast skip never binds** in any segment (largest: gaming random items, +0.58 pp at 1.388%, +1.80%).

### Watch list (binding point uncertain)
Six segments cross the hate limit inside the observed range, but each one's interval at 1.388% runs
from below the limit to above it, so the data cannot say whether or where they bind. They are not a
basis for a lower share; they are candidates to watch in a new test.

| Segment | Binding share (point) | Hate at 1.388% [95% CI] | Limit (2% of baseline) |
|---|---:|---|---:|
| Tenure 181-365 days (users) | 0.80% | +0.0021 pp [+0.0010, +0.0035] | +0.0012 pp |
| Short drama (items) | 1.09% | +0.0013 pp [+0.0007, +0.0018] | +0.0010 pp |
| Music (items) | 1.12% | +0.0013 pp [+0.0007, +0.0019] | +0.0010 pp |
| Anime (items) | 1.19% | +0.0012 pp [+0.0008, +0.0017] | +0.0010 pp |
| Art (items) | 1.31% | +0.0011 pp [+0.0004, +0.0018] | +0.0010 pp |
| Activity tercile 2 (users) | 1.36% | +0.0011 pp [+0.0007, +0.0016] | +0.0011 pp |

- **The tenure 181-365 result is isolated.** Both neighbouring tenure bands stay under the limit at
  1.388% (merged band 8-14 to 91-180 days: +0.0013 pp against a limit of +0.0025 pp; 366-730 days:
  +0.0012 pp against +0.0014 pp), so there is no gradient with tenure. It is also the smallest tenure
  band (1,743 users), and its hate contrast with the rest of the dimension is a BH lead (bootstrap only),
  not a finding (see Segments).
- **32 of 45 rows are flagged** because a guardrail's interval crosses the limit somewhere in the range;
  in all of them the guardrail is hate, whose intervals are wide because hate is rare. Fast skip is
  never flagged.
- Item-segment rows (category, duration) answer which content to explore with, not which users; the
  budget does not add exploration beyond the observed range for any segment.

## Hypotheses
- **H1 (cost): supported.** Random slots cost on every identifiable engagement metric, and raise both
  identifiable guardrails (hate, fast skip).
- **H2 (hidden session cost): not testable.** Session exit is not identifiable from these logs (D53).
- **H3 (discovery benefit): not supported.** Per impression, random slots produce fewer new-author
  follows (−85%) and fewer new-category effective views (−31%) than recommended slots in the same
  request.
- **H4 (heterogeneity): supported, mainly by content.** The cost of a random slot varies most with the
  random item's category and length; user segments differ by a few points, and which users "tolerate"
  exploration best depends on absolute vs relative terms. New-category engagement from random slots
  matches recommended slots for active users and falls short for low-activity users (partly mechanical).

## Limitations
- **No discovery benefit in the short run, and no way to see a long-run one.** Random slots lead to
  fewer effective views in a new category than recommended slots (1.21% vs 1.76% of impressions,
  −0.55 pp) and to fewer follows of new creators. So in this data, exploration buys no discovery in the
  short run. The case for exploration rests on long-run effects, such as users finding new interests
  and the recommender learning from what they do. The test window is 16 days, and these logs cannot
  measure those effects.

## Exploration budget (D54, D56, D57)
- The budget uses the item-level guardrails only; session-level impact is not identifiable from these
  logs, and the budget says so (D54).
- Hate is a finding (D56) and constrains the budget as in D48 (D57, decided after A results and before
  any B, C, segment or budget outcome).

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
