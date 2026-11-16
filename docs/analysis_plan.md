# Analysis Plan (pre-registration)

Status: **FINAL**, tagged `prereg-v1` on 2026-11-16 before any effect query ran. The Phase 0 health
checks (`docs/data_quality.md`) looked only at data structure, never at random-vs-recommended outcomes.
Changes made after the health checks and before any outcome analysis are marked _post-hoc_ (D15-D25).
Parameters marked as proposed in the draft are locked at the values shown. Any later change is logged
in `docs/decisions.md` and reported as a deviation from this plan.

## Question
What share of feed impressions should go to exploration, and should that share differ by user segment?

## Windows
| Window | Dates | Use |
| --- | --- | --- |
| Pre-period | 2022-04-08 to 2022-04-21 | Segments, user history, reference distributions. Never measures effects |
| Treatment | 2022-04-23 to 2022-05-08 | Random (`is_rand = 1`) and recommended (`is_rand = 0`) exposures, **tab 1 only** (_post-hoc_, D15). April 22, a partial first day, is excluded (_post-hoc_, D22) |

Insertion-rate regimes within the treatment window (_post-hoc_, D17, D22; HC 1c): low = 04-23 to 05-01
(tab-1 random share 0.658% of exposures, 3.59% of requests), transition = 05-02 (1.018%, 5.58%), high =
05-03 to 05-08 (1.388%, 7.55%). The switch coincides with the May Day holiday. Regimes are never
compared before vs after. A request holds 5.4-5.5 items and never more than one random item.

## Primary metric (one, locked)
**Duration-adjusted effective view rate**: share of impressions where watch time reaches the
50th percentile of watch time for videos in the same duration bucket.
- Duration buckets: deciles of `duration_ms`.
- Reference distribution: built from **tab-1 pre-period recommended impressions only** (2022-04-08 to
  04-21, `tab = 1`), then frozen, so the threshold cannot depend on treatment-window outcomes of either
  arm and matches the tab-1 analysis population (_post-hoc_, D25).
- Duration (_post-hoc_, D19, D23): `duration_ms` from the log; if null or non-positive, filled from
  `video_features_basic.video_duration`. Rows still missing are excluded from every metric in the main
  run. They are not a distinct content type (HC 4c: all NORMAL videos, spread across upload periods,
  missing in every exposure of the video). The missing rate by `is_rand` is reported with every primary
  result (HC 4c: 7.86% recommended vs 3.05% random, dev sample).

## Secondary, discovery and guardrail metrics
| Tier | Metric | Definition |
| --- | --- | --- |
| Secondary | Like, comment, forward, profile-enter rate | `is_like`, `is_comment`, `is_forward`, `is_profile_enter` per impression |
| Secondary | Naive completion rate, naive watch time | Reported next to the primary metric to show length bias |
| Discovery | New-author follow rate | Follow of an author with no interaction in the pre-period |
| Discovery | New-category engagement rate | Effective view in a category with no effective view in the pre-period |
| Guardrail | Hate rate | `is_hate` per impression |
| Guardrail | Fast-skip rate | `play_time_ms` < 3,000 ms |
| Guardrail | Session-exit rate | Session ends within the next N = 3 impressions |

Sessions: consecutive impressions of a user with gaps under 30 minutes (from `time_ms`).

## Comparisons
- **A, feed request (primary, _post-hoc_, D18):** for each random item, random minus the mean of the
  recommended items in the same request (same `user_id` and `time_ms`, tab 1), averaged over requests.
  Always within day; regime enters as a control. Robustness: within-user mean difference, random minus
  recommended, tab 1, within day.
- **Weighting (_post-hoc_, D21):** equal weight per user. Compute each user's mean within-request
  difference (within-user difference for the robustness check), then average across users. Robustness:
  population-reweighted results, weighting each user by their number of random requests (equivalent to
  pooling all requests). Equal shares of random items across users are not required: comparisons are
  within request and within user, and the slot choice is random (HC 1c: no request has two random items;
  daily request-level rates are stable within each regime).
- **B, same video:** pool videos only (the 7,583 candidates), recommended vs random exposure.
- **C, decomposition:** total gap = content gap (pool vs typical recommended) + targeting gap (B).

## Inference
- User-clustered bootstrap, B = 2,000 resamples, seed = 20261115, 95% percentile intervals.
- Cross-check: OLS with request fixed effects for the primary (user fixed effects for the robustness
  check); controls for hour, duration bucket, day and regime (regime is absorbed by day fixed effects);
  SEs clustered by user. Tab is constant (tab 1) and no longer a control (_post-hoc_, D15).
- Sensitivity runs, each reported next to the main result:
  - excluding the top 0.1% of user-days by exposure count (_post-hoc_, D20);
  - non-duration metrics (secondary, discovery, hate rate) with the missing-duration rows included
    (_post-hoc_, D23);
  - excluding the AD-marked pool videos from the random arm; they stay in the main run (_post-hoc_, D24).
- A headline result requires both methods to agree in sign and significance.
- Segments: Benjamini-Hochberg at q = 0.10. Results failing correction are reported as leads.
- Minimum detectable effects are computed per segment before outcomes are read; segments below the
  threshold of 80% power for a 1-point change in the primary metric are merged.

## Segments (pre-period only)
Pre-period activity terciles; tenure (`register_days_range`); `user_active_degree`; follow-count bands;
duration buckets; `video_type` and category (from the supplementary category file only, _post-hoc_, D20).

### `user_active_degree` merge rule (locked, decision D14)
Uses only user counts per level in `user_features` (27,285 users), never outcome data.

| Level | Users | Merged group |
| --- | ---: | --- |
| full_active | 17,959 | full_active |
| high_active | 6,158 | high_active |
| middle_active | 2,133 | middle_active |
| 2_14_day_new | 635 | new_or_low |
| low_active | 300 | new_or_low |
| single_low_active | 68 | new_or_low |
| 30day_retention | 15 | new_or_low |
| day_new | 11 | new_or_low |
| UNKNOWN | 6 | none (excluded from this dimension's segment tests; kept in overall results) |

Procedure, applied in order:
1. Minimum group size: 1,000 users (about 3.7% of users; at the overall rate of about 43 random
   exposures per user, about 43,000 random exposures per group).
2. Levels at or above the minimum stay as they are.
3. Levels below it first join their own family: new-user levels (day_new, 2_14_day_new,
   30day_retention) form `new` (661); low-activity levels (low_active, single_low_active) form `low` (368).
4. A group still below the minimum merges with the smallest other group below the minimum; if none is
   left, with the adjacent group in activity order (high > full > middle > low). Here `new` (661) and
   `low` (368) merge into `new_or_low` (1,029).
5. The minimum-detectable-effect rule above can merge groups further; it cannot split them.

## Exploration budget
Guardrail limit: no guardrail metric worsens by more than 2% relative at the feed level.
Interpolate only within observed random-insertion rates: the tab-1 random share of 0.658% (low regime)
to 1.388% (high regime) of exposures (_post-hoc_, D17, D22; HC 1c).
