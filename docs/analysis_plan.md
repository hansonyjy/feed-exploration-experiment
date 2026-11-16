# Analysis Plan (pre-registration)

Status: **FINAL**, tagged `prereg-v1` on 2026-11-16 before any effect query ran. The Phase 0 health
checks (`docs/data_quality.md`) looked only at data structure, never at random-vs-recommended outcomes.
Changes made after the health checks and before any outcome analysis are marked _post-hoc_ (D15-D48).
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

## General rules (_post-hoc_)
- Every locked threshold, bucket edge, baseline and flag is computed on **full data** from the
  deduplicated staging tables, never on the 5% dev sample. Numbers in this plan marked "dev sample" are
  illustrations and are recomputed on full data for the memo (D27).
- `user_features` (tenure, follow counts, activity level) is a static snapshot of unknown date. It is
  treated as pre-treatment, and this is stated as a limitation in the memo (D28).

## Primary metric (one, locked)
**Duration-adjusted effective view rate**: share of impressions with an effective view.
- Effective view: `play_time_ms` ≥ the median `play_time_ms` of the reference impressions in the same
  duration bucket (ties count as effective) (_post-hoc_, D29).
- Reference distribution: built from **tab-1 pre-period recommended impressions only** (2022-04-08 to
  04-21, `tab = 1`), then frozen, so the threshold cannot depend on treatment-window outcomes of either
  arm and matches the tab-1 analysis population (_post-hoc_, D25). Reference rows use the same duration
  rule as the analysis rows and are deduplicated (_post-hoc_, D30).
- Duration buckets: deciles of duration, with edges computed on tab-1 pre-period recommended impressions
  with a valid duration after the fill rule; the bottom and top buckets are open-ended (_post-hoc_, D26).
- Duration (_post-hoc_, D19, D23): `duration_ms` from the log; if null or non-positive, filled from
  `video_features_basic.video_duration`. Rows still missing are excluded from every metric in the main
  run. They are not a distinct content type (HC 4c: all NORMAL videos, spread across upload periods,
  missing in every exposure of the video). The missing rate by `is_rand` is reported with every primary
  result (HC 4c: 7.86% recommended vs 3.05% random, dev sample).

## Secondary, discovery and guardrail metrics
| Tier | Metric | Definition |
| --- | --- | --- |
| Secondary | Like, comment, forward, profile-enter rate | `is_like`, `is_comment`, `is_forward`, `is_profile_enter` per impression |
| Secondary | Naive completion rate | `play_time_ms` ≥ `duration_ms` (after the fill), on the same rows as the primary metric (_post-hoc_, D31) |
| Secondary | Naive watch time | `play_time_ms` per impression. Both naive metrics are reported next to the primary metric to show length bias |
| Discovery | New-author follow rate | Impressions with `is_follow = 1` on a new author, over all impressions in the arm. New author: the user had no exposure to any video by that `author_id` (from `video_features_basic`) in the pre-period, on any tab. Earlier treatment-window exposures do not change who counts as new (_post-hoc_, D32, D33) |
| Discovery | New-category engagement rate | Impressions with an effective view in a new category, over all impressions in the arm. Category: first level from the supplementary file. New category: no effective view (D25/D26/D29 rule) in that category in the pre-period, on any tab. Videos without a first-level category cannot count as new and stay in the denominator (_post-hoc_, D34) |
| Guardrail | Hate rate | `is_hate` per impression |
| Guardrail | Fast-skip rate | `play_time_ms` < 3,000 ms |
| Guardrail | Session-exit rate | The session ends within this request or the next 2 requests (N = 3, counted in requests because items in a request share a timestamp) (_post-hoc_, D36) |

Sessions: consecutive exposures of a user with gaps under 30 minutes (from `time_ms`), built from both
logs, all tabs and the full period 2022-04-08 to 05-08 so that sessions are not cut at window edges;
only tab-1 exposures from 04-23 to 05-08 are scored (_post-hoc_, D35). Exposures in the last 30 minutes
of 2022-05-08 (Asia/Shanghai) are excluded from the session-exit metric because their session may be
cut off by the end of the data (_post-hoc_, D38).

## Comparisons
- **A, feed request (primary, _post-hoc_, D18):** for each random item, random minus the mean of the
  recommended items in the same request (same `user_id` and `time_ms`, tab 1), averaged over requests.
  Always within day; regime enters as a control. Robustness: within-user mean difference, random minus
  recommended, tab 1, within day.
- **Session exit in A (_post-hoc_, D37):** every item in a request shares the session outcome, so a
  within-request difference is zero by construction. For session exit only, requests containing a random
  item are compared with requests without one, within user and day, with the same weighting.
- **Weighting (_post-hoc_, D21):** equal weight per user. Compute each user's mean within-request
  difference (within-user difference for the robustness check), then average across users. Robustness:
  population-reweighted results, weighting each user by their number of random requests (equivalent to
  pooling all requests). Equal shares of random items across users are not required: comparisons are
  within request and within user, and the slot choice is random (HC 1c: no request has two random items;
  daily request-level rates are stable within each regime).
- **B, same video (_post-hoc_, D43):** tab 1, treatment window, pool videos (the 7,583 candidates) with at
  least one exposure in each arm. Per video, random minus recommended; equal weight per video; bootstrap
  clustered by video, with a user-clustered bootstrap as robustness.
- **C, decomposition (_post-hoc_, D44):** all terms on tab 1 in the treatment window with the same user
  weighting as A: total gap = rec(all) − rand; content gap = rec(all) − rec(pool videos); targeting gap =
  rec(pool videos) − rand. The parts add up exactly. B's video-weighted estimate is reported beside it.

## Inference
- User-clustered bootstrap, B = 2,000 resamples, seed = 20261115, 95% percentile intervals.
- Cross-check: OLS with request fixed effects for the primary (user fixed effects for the robustness
  check); controls for hour, duration bucket, day and regime (regime is absorbed by day fixed effects);
  SEs clustered by user. Tab is constant (tab 1) and no longer a control (_post-hoc_, D15). Hour comes
  from `hourmin` as provided (HC 10); duration buckets use the D26 edges (_post-hoc_, D41).
- Sensitivity runs, each reported next to the main result:
  - excluding the top 0.1% of user-days by exposure count, computed on full data from both logs, all
    tabs, 2022-04-08 to 05-08 (_post-hoc_, D20, D42);
  - non-duration metrics (secondary, discovery, hate rate) with the missing-duration rows included
    (_post-hoc_, D23);
  - excluding the AD-marked pool videos from the random arm; they stay in the main run (_post-hoc_, D24).
- A headline result requires both methods to agree in sign and significance.
- Segments: Benjamini-Hochberg at q = 0.10. Results failing correction are reported as leads.
- Minimum detectable effects are computed per segment before outcomes are read; segments below the
  threshold of 80% power for a 1-point change in the primary metric are merged. Inputs (_post-hoc_, D39):
  baseline rate, variance and within-user correlation from tab-1 pre-period recommended impressions (no
  treatment outcomes); random requests per segment from treatment-window counts; two-sided α = 0.05;
  1 point = 1 percentage point absolute; user-clustered design. Merge order (_post-hoc_, D40): with the
  adjacent segment in the dimension's natural order (for categories, with the smallest segment), repeated
  until every segment passes.

## Segments (pre-period only)
- Pre-period activity terciles (_post-hoc_, D45): count of pre-period exposures across all tabs, split
  with `ntile(3)` over users with any; users with none form `no_pre_period`.
- Tenure (`register_days_range`) and follow-count bands (`follow_user_num_range`) as provided, merged
  with the D14 rule: at least 1,000 users per band, merging adjacent bands (_post-hoc_, D46).
- `user_active_degree`: merged groups below (D14).
- Duration buckets: the D26 deciles of the random item's duration (_post-hoc_, D47).
- `video_type` and category: first-level category of the random item from the supplementary category
  file only (_post-hoc_, D20). Categories with fewer than 1,000 random exposures in the window (a count,
  not an outcome) merge into `other` (_post-hoc_, D47).

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
Guardrail limit: no guardrail metric worsens by more than 2% relative at the feed level (_post-hoc_, D48).
- Baseline: the user-weighted rate of tab-1 recommended exposures, within day, in the treatment window
  (the feed without exploration).
- Item-level guardrails (hate rate, fast-skip rate): s is the share of tab-1 exposures that are random.
  The feed-level change at share s is s × (rand − rec) / rec, which must stay at or below 2%. s is
  interpolated only between the observed exposure shares, 0.658% (low regime) and 1.388% (high regime)
  (_post-hoc_, D17, D22; HC 1c).
- Session exit, measured per request (D37): s is the share of tab-1 requests containing a random item.
  The feed-level change at share s is s × (rand − rec) / rec using the request-level rates, which must
  stay at or below 2%. s is interpolated only between the observed request shares, 3.59% and 7.55%.
- The budget table reports both shares for each segment.
