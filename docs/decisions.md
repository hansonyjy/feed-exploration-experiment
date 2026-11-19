# Decision Log

Each entry: date, decision, alternatives considered, reason. Newest first.

## 2026-11-18 · D52 · Post-results exploratory diagnostics on session exit (primary analysis unchanged)
- Post-results: decided 2026-11-18 after the dev Comparison A results were seen. Exploratory; it does
  not change the primary analysis or any pre-registered estimate.
- What was seen: on dev, requests with a random item were 5.0 pp (17%) less likely to be within the last
  three requests of their session, the opposite of H2.
- Why: the contrast may reflect how the logs were recorded rather than an effect of the random item.
- Diagnostics (counts only, full raw data, tab-1 requests 2022-04-23 to 05-08 excluding censored ones,
  sessions cut across all tabs as in D35):
  1. Insertion rate by session position: first request, middle requests, and each of the last three.
     Positions from the end are the session-exit outcome restated, so only the first-request rate tests
     position-dependent insertion; the item cannot change whether its request opens a session.
  2. Display truncation: tab-1 items per request for requests with and without a random item, for a
     session's final request vs other requests, and the insertion rate by items per request.
- Decision rules, fixed before running (relative differences; full-data samples make noise negligible):
  - Position explains the gap if the first-request insertion rate differs from the middle-request rate
    by more than 5%.
  - Truncation explains the gap if both hold: final requests show at least 5% fewer tab-1 items than
    other requests, and among non-final requests the insertion rate in requests with the modal item
    count is at least 5% higher than in smaller requests.
  - If either rule fires, session exit is reported as not identifiable from these logs, with no
    direction claimed, and H2 cannot be tested with this data.

## 2026-11-18 · D51 · Metric-layer details the plan leaves open (before any outcome was seen)
- Decided 2026-11-18 while building the metric layer, before any outcome query ran. Implementation
  details; they do not change the plan.
- Request contrasts (D18) in the main run need a random item with a valid duration and at least one
  recommended item in the same request with a valid duration (D23). With the missing-duration rows
  included (the D23 sensitivity run), non-duration metrics use every item.
- Session exit (D37) in the main run: requests whose random item lacks a valid duration are excluded;
  requests without a random item are all kept, since they have no random item to exclude. The D23
  sensitivity run keeps every request. Censored requests (D38) are always excluded.
- New-author follow (D33): an impression whose video has no author_id cannot be a new-author follow.
- Duration-based metrics (effective view, naive completion, new-category effective view) are null for
  rows without a valid duration; non-duration metrics (watch time, like, comment, forward, profile
  enter, new-author follow, hate, fast skip) are defined on every row.

## 2026-11-18 · D50 · Phase 1 implementation choices (approved before any outcome was seen)
- Decided 2026-11-18 when planning Phase 1, before any outcome query ran. These fill in details the
  plan leaves open; they do not change it.
- Exact quantiles: decile edges (D26) and bucket medians (D29) are the smallest value whose cumulative
  share is at least k/10 (or 50%), computed exactly from value counts, not BigQuery's approximate
  quantiles. A duration equal to an edge falls in the lower bucket.
- Freezing: on dev, edges and medians come from the dev sample and are provisional. At the prod build the
  full-data edges and medians are written to committed dbt seeds, which every target then reads (D25, D27).
- Regression weighting: weighted OLS in which each user's observations sum to 1, matching the
  equal-user point estimate (D21); the unweighted regression is the population-reweighted robustness check.
- Session requests: sessions and the "next 2 requests" rule (D36) count requests across all tabs (D35).

## 2026-11-18 · D49 · Deviation: primary item-level regression without the duration-bucket control
- Deviation from prereg-v1, decided 2026-11-18 before any outcome was seen. prereg-v1 is not moved.
- Was (analysis_plan.md, Inference): OLS with request fixed effects and controls for hour, duration
  bucket, day and regime.
- Now: the primary regression for item-level metrics uses request fixed effects without the
  duration-bucket control (hour, day and regime are constant within a request and absorbed). The
  bucket-controlled regression is reported beside it as a diagnostic.
- Reason: random items are longer than recommended items (HC 2: median 81 s vs 34 s), so controlling for
  duration bucket changes the estimand from the total cost of an exploration slot to the cost at equal
  length. The point estimate measures the total slot cost, and the primary metric is already
  duration-adjusted, so the regression without the control is the like-for-like cross-check.

<!-- D26-D48 were logged together after a sweep of analysis_plan.md for parameters without a stated
     source population, date range or tab. prereg-v1 moved once, to the commit that adds them. -->

## 2026-11-16 · D48 · Guardrail baseline and exploration share by guardrail type
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Baseline = user-weighted rate of tab-1 recommended exposures, within day, in the treatment window. Item-level guardrails (hate, fast skip): s = exposure share, change = s x (rand - rec) / rec <= 2%, s interpolated between 0.658% and 1.388%. Session exit (per request, D37): s = share of tab-1 requests with a random item, same formula on request-level rates, s interpolated between 3.59% and 7.55%. The budget table reports both shares.
- Reason: The 2% limit had no stated baseline, and session exit is measured per request, so it needs a request-level share.

## 2026-11-16 · D47 · Category and duration segments
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Segments use the random item's first-level category and D26 bucket; categories with fewer than 1,000 random exposures in the window (a count) merge into other.
- Reason: Keeps small categories from producing unstable segment estimates.

## 2026-11-16 · D46 · Tenure and follow-count bands merged by the D14 rule
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Provided bands, merged so each has at least 1,000 users, merging adjacent bands.
- Reason: Some bands are tiny (for example 8-14 days of tenure).

## 2026-11-16 · D45 · Pre-period activity terciles
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Count of pre-period exposures across all tabs, ntile(3) over users with any; users with none form no_pre_period.
- Reason: Matches the definition used in the health checks, now stated in the plan.

## 2026-11-16 · D44 · Comparison C: additive decomposition with user weighting
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: All terms on tab 1 in the window with A's user weighting: total = rec(all) - rand; content = rec(all) - rec(pool); targeting = rec(pool) - rand. B's video-weighted estimate is reported beside it.
- Reason: "Typical recommended" was undefined, and mixed weightings would not add up.

## 2026-11-16 · D43 · Comparison B: population, weighting, clustering
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Tab 1, treatment window; pool videos with at least one exposure in each arm; per video, random minus recommended; equal weight per video; bootstrap clustered by video, with user-clustered as robustness.
- Reason: B was defined only as "recommended vs random" for pool videos.

## 2026-11-16 · D42 · Population for the top 0.1% user-day flag
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Full data, both logs, all tabs, 2022-04-08 to 05-08.
- Reason: HC 6 used the dev sample; the analysis flag needs a stated population.

## 2026-11-16 · D41 · Hour and duration-bucket controls
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Hour from hourmin as provided (HC 10); duration buckets use the D26 edges.
- Reason: The sources of the regression controls were not stated.

## 2026-11-16 · D40 · MDE merge order
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Merge with the adjacent segment in the dimension's natural order (for categories, the smallest segment), repeated until every segment passes.
- Reason: The merge order was not stated.

## 2026-11-16 · D39 · MDE and power inputs
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Baseline rate, variance and within-user correlation from tab-1 pre-period recommended impressions; random requests per segment from treatment-window counts; two-sided alpha 0.05; 80% power; 1 point = 1 percentage point absolute; user-clustered design.
- Reason: The inputs were not stated; pre-period data keeps them free of treatment outcomes.

## 2026-11-16 · D38 · Session exit: exclude right-censored exposures
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Exposures in the last 30 minutes of 2022-05-08 (Asia/Shanghai) are excluded from the session-exit metric.
- Reason: Their sessions may be cut off by the end of the data.

## 2026-11-16 · D37 · Session exit compared at the request level
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: For session exit only, requests with a random item are compared with requests without one, within user and day, with the D21 weighting.
- Reason: Every item in a request shares the session outcome, so a within-request difference is zero by construction.

## 2026-11-16 · D36 · Session exit counted in requests
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: N = 3 means the session ends within this request or the next 2 requests.
- Reason: Items in a request share a timestamp, so their order within the request is unknown.

## 2026-11-16 · D35 · Session construction
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Sessions use both logs, all tabs and 2022-04-08 to 05-08 (30-minute gap rule on time_ms); only tab-1 exposures from 04-23 to 05-08 are scored.
- Reason: Building from all exposures avoids cutting sessions at the tab or window boundary.

## 2026-11-16 · D34 · New category: first level, pre-period effective views on any tab
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Category = first level from the supplementary file. New = no effective view (D25/D26/D29 rule) in that category in the pre-period, any tab. Videos without a first-level category cannot count as new and stay in the denominator.
- Reason: The level, tabs and effective-view rule were not stated.

## 2026-11-16 · D33 · New-author follow rate: numerator and denominator
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Numerator: impressions with is_follow = 1 on a new author; denominator: all impressions in the arm. History is the pre-period only.
- Reason: Fixes the rate's definition and keeps newness from depending on treatment-window exposures.

## 2026-11-16 · D32 · New author: no pre-period exposure on any tab
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: An author is new to a user if the user had no exposure to any video by that author_id (video_features_basic) in the pre-period, on any tab.
- Reason: "No interaction" was ambiguous; exposure is the strictest test of "seen before".

## 2026-11-16 · D31 · Naive completion rate defined
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: play_time_ms >= duration_ms (after the fill), on the same rows as the primary metric.
- Reason: The metric was named but not defined.

## 2026-11-16 · D30 · Reference rows use the analysis duration rule and are deduplicated
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: The D19/D23 fill-and-exclude rule applies to the reference rows, which come from deduplicated staging.
- Reason: Keeps the threshold and the rows it is applied to on the same footing.

## 2026-11-16 · D29 · Effective view: play_time_ms at or above the bucket median
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Effective view = play_time_ms >= the median play_time_ms of reference impressions in the same duration bucket; ties count as effective.
- Reason: "Reaches the 50th percentile" left the column and tie handling open.

## 2026-11-16 · D28 · user_features treated as pre-treatment
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Tenure, follow counts and activity level come from a static snapshot of unknown date; they are treated as pre-treatment and the memo states this as a limitation.
- Reason: The snapshot date is not documented, so the assumption is made explicit rather than implied.

## 2026-11-16 · D27 · Locked quantities come from full data
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Every locked threshold, edge, baseline and flag is computed on full data from deduplicated staging; dev-sample numbers in the plan are illustrations, recomputed on full data for the memo.
- Reason: The plan did not say which data the parameters come from; the 5% sample is for development only.

## 2026-11-16 · D26 · Duration-bucket decile edges from tab-1 pre-period impressions
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: Edges are deciles of duration over tab-1 pre-period recommended impressions with a valid duration after the fill rule; bottom and top buckets are open-ended.
- Reason: The plan said "deciles of duration_ms" without a source population; this matches the D25 reference distribution.

## 2026-11-16 · D25 · Effective-view reference distribution from tab-1 pre-period impressions
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: the watch-time percentiles behind the primary metric come from tab-1 pre-period recommended
  impressions only (2022-04-08 to 04-21, `tab = 1`), then frozen.
- Reason: the plan said "pre-period recommended impressions" without a tab restriction, while D15 limits
  the analysis population to tab 1. Mixing tabs would set the effective-view bar from surfaces with
  different viewing behaviour than the population it is applied to.
- prereg-v1 moved from 2894e26 to the commit that adds this entry, before any outcome query ran.

## 2026-11-16 · D24 · AD-marked pool videos: keep in the main run, drop in a sensitivity run
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- 1.0% of pool videos are marked AD although the paper says ads were filtered out (HC 2, HC 8). They
  stay in the main run, since they were part of the random policy as served, and are excluded from the
  random arm in a sensitivity run.

## 2026-11-16 · D23 · Missing-duration rule settled by profiling (refines D19)
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- HC 4c profiled tab-1 rows still missing a duration after the fill, by arm, video_type and upload
  period, under a rule fixed before the run (a distinct content type holds >= 80% of missing rows and
  <= 20% of rows with a duration, in both arms). Result: none. All missing rows are NORMAL videos,
  spread across upload periods, and every one comes from a video missing in all its exposures.
- Rule: exclude the missing rows from every metric in the main run; report the gap by arm (7.86%
  recommended vs 3.05% random, dev sample); run the non-duration metrics with and without those rows.

## 2026-11-16 · D22 · Exclude April 22 from the analysis window
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- April 22 is the first day of the random policy and a partial day (tab-1 random share 43% below the
  rest of the low regime, HC 1b). The analysis window is 2022-04-23 to 05-08; the low-regime rate becomes
  0.658% of exposures (HC 1c).

## 2026-11-16 · D21 · HC 1 segment criterion non-blocking; equal weight per user
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Justification: Comparison A is within request and within user, so validity requires that the slot
  given to the random item is chosen at random, not that every user receives the same share of random
  items. HC 1c supports a random slot choice: no request holds more than one random item, and daily
  request-level rates are stable within each regime (max deviation +9.9% low, -4.9% high). The segment
  differences remain (light pre-period users +73% to +77% at the request level) and are reported.
- Reclassified: the segment criteria of HC 1, 1b and 1c are non-blocking, whatever HC 1c showed.
- Weighting rule, locked in analysis_plan.md: equal weight per user (within-user differences first,
  then averaged across users), so heavily exposed users do not dominate; population-reweighted results
  (weight = the user's random requests) as a robustness check.

## 2026-11-16 · D20 · Health-check follow-ups: HC 5 accepted, HC 6 and HC 11 re-specified, HC 8 from the paper
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- HC 5: exact duplicates (0.65-0.87% of standard rows) and key conflicts (0.10-0.12%) are accepted and
  documented; D13 stands and impression_id uniqueness stays warn-level.
- HC 6: the 2,000-exposures-per-day bar sat below the user-day p99 (2,521) and flagged 13.7% of users.
  Replaced by flagging the top 0.1% of user-days, which stay in the main analysis and are excluded in
  a sensitivity run.
- HC 11: categories come from the supplementary file only; the tag-agreement criterion (74.6% vs a
  90% bar) is dropped because the two taxonomies need not match.
- HC 8: pool selection documented from the paper (Sec. 3.2), with the data's contradictions noted.

## 2026-11-16 · D19 · Duration rule for the primary metric
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: use `duration_ms` from the log; where it is null or non-positive, fill it from
  `video_features_basic.video_duration`; exclude rows still missing. Report the missing rate by
  `is_rand` with every primary result (a property of the exposure, not an outcome).
- HC 4b (dev): 7.84% of recommended and 3.06% of random tab-1 rows lack a duration, and the fill
  recovers almost none, so the exclusion is unequal across arms and must be reported.
- Alternatives: impute from the video's median watch time (uses outcomes); drop the duration adjustment.

## 2026-11-16 · D18 · Primary Comparison A unit: the feed request
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Primary: each random item vs the recommended items in the same feed request, i.e. sharing its
  `user_id` and `time_ms` in tab 1. The within-user comparison (D6) becomes a robustness check.
- Reason: HC 9 showed random items are logged separately from the rest of the same request (97.0%
  of random rows share user and time_ms with standard rows), so the request holds user, moment and
  context fixed. Random rows with no matching request (3.0%) are left out of the primary estimate and
  kept in the within-user check.

## 2026-11-16 · D17 · Insertion-rate regimes and the May Day holiday
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- The tab-1 random share is 0.630% from 2022-04-22 to 05-01, 1.018% on 05-02 and 1.388% from
  05-03 to 05-08 (HC 1b). The switch coincides with China's May Day holiday (about Apr 30 to May 4).
- Rule: never compare regimes before vs after. Compare random and recommended within day (and within
  request); include regime as a control (absorbed when day fixed effects are in the model). The
  budget interpolates only between the two observed rates, 0.630% and 1.388%.
- Alternatives: analyze the low regime only (loses 45.7M tab-1 exposures); treat the rate as constant.

## 2026-11-16 · D16 · Re-specify HC 1 within tab 1 and within each date regime
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- HC 1 failed on all tabs because insertion ran almost only on tab 1 and the rate changed mid-window.
  HC 1b judges day and segment stability within tab 1 and within each regime (05-02 reported only).
- Result: still FAILS. High-regime days pass; segments do not (light pre-period users +79% to +87%).
  Diagnostic d01: random exposures are roughly constant per user (median 21-23 per activity tercile)
  rather than proportional to exposures. Open; prereg-v1 is not tagged.

## 2026-11-16 · D15 · Analysis population: tab 1 in the treatment window
- Post-hoc: decided 2026-11-16 after the Phase 0 health checks, before any outcome analysis.
- Rule: all random-vs-recommended comparisons use tab-1 exposures from 2022-04-22 to 05-08.
- Reason: 99.3% of random exposures are on tab 1 (HC 7); other tabs have no comparable random arm.
  The pre-period still uses all tabs for profiles and history.

## 2026-11-16 · D14 · Merge the 8 user_active_degree levels into 4 groups by user count
- Rule (locked in analysis_plan.md before prereg-v1): minimum 1,000 users per group; small levels join
  their family first (new-user levels, low-activity levels), then the smallest under-size groups merge.
  Result: full_active 17,959, high_active 6,158, middle_active 2,133, new_or_low 1,029; 6 UNKNOWN
  users are excluded from this dimension only.
- Alternatives: keep the 3 documented levels and drop the other 1,029 users; merge new users into
  tenure instead (tenure is already its own dimension).
- Reason: the data has 8 levels, not the documented 3 (data_quality.md #12), and five of them are too
  small to analyze alone. The rule uses counts only, so it cannot be tuned to results.

## 2026-11-16 · D13 · Staging dedupe rule: collapse exact duplicates only
- Rule: in `stg_log_standard` and `stg_log_random`, rows identical in every source column collapse to
  one (`select distinct`). Rows that share (source table, user_id, video_id, time_ms) but differ in
  any other column are all kept; `impression_id` (md5 of those four) is then not unique, and its
  uniqueness test stays warn-level until HC 5 explains those rows.
- HC 5 counts both kinds on the raw tables, before this rule applies, so the amount removed is on
  record (`docs/data_quality.md` #5).
- Alternatives: keep exact duplicates (double-counts exposures); keep one row per key (silently
  picks between conflicting rows before we know what they mean).
- Reason: exact copies carry no information, while conflicting rows may be real repeat exposures
  within the same millisecond batch, so they are not dropped until HC 5 says what they are.
  First dev build: 8,551 non-unique impression_ids in `stg_log_standard`, 0 in `stg_log_random`.

## 2026-11-16 · D12 · Dev sample: 5% of users by md5, materialized at load time
- Rule: `mod(cast(concat('0x', substr(to_hex(md5(cast(user_id as string))), 1, 8)) as int64), 100) < 5`
  in BigQuery; the load script computes the same with Python `hashlib`, and `verify` checks that
  both select the identical user list. Sampled log copies live in `raw.*_dev5`.
- Alternatives: filter by hash inside dev models (scans the full raw tables on every dev run, since a
  hash filter cannot use clustering); `user_id < k` (prunes, but not a random sample).
- Reason: dev runs read about 5% of the bytes, and whole users are kept, so user-level checks and
  within-user comparisons stay valid on the sample.

## 2026-11-16 · D11 · Load route: CSV to typed Parquet with DuckDB, then BigQuery load jobs
- Alternatives: load the CSVs as-is and derive `event_date` with a CTAS (about 50 GB billed);
  integer-range partitioning on the YYYYMMDD `date` column.
- Reason: `event_date` is derived locally, so the partitioned, clustered raw tables come straight
  from free load jobs with no query cost. Parquet is typed and several times smaller to upload.
  Raw keeps every source column unchanged; the only addition is `event_date`. DuckDB is used only
  as a file converter (D4 still holds).

## 2026-11-16 · D10 · Video categories from the KuaiRand supplementary file
- Source: `kuairand_video_categories.csv`, Zenodo record 18159199 (CC BY 4.0, by the KuaiRand
  author), loaded as `raw.video_categories`. Four category levels with model probabilities; a missing
  level is id -124 / name UNKNOWN.
- Alternatives: the `tag` column in `video_features_basic` (ids only, meanings undocumented).
- Reason: needed for the category segments and the new-category discovery metric. The file joins on
  `final_video_id`, which the dataset site calls consistent with KuaiRand but does not map to 27K
  `video_id` explicitly; the join coverage is checked in Phase 0 before any category result is used.

## 2026-11-16 · D9 · Cluster raw log tables by user_id, video_id (was user_id, is_rand)
- Alternatives: user_id, is_rand (the original plan); user_id only.
- Reason: random and standard exposures live in separate raw tables, so `is_rand` is constant within
  each table and clustering on it prunes nothing. `video_id` as the second key speeds up the joins
  and filters that matter here: the 7,583 pool videos in Comparison B and the video feature and
  category joins. Partitioning by `event_date` is unchanged. CLAUDE.md and design.md updated.

## 2026-11-15 · D7 · Static web dashboard first, Tableau Public as a supplement
- Alternatives: Tableau Public only; Looker Studio.
- Reason: a custom page reads static exports, costs nothing to host, and supports the budget simulator.
  Two views are rebuilt in Tableau Public so the tool is evidenced too.

## 2026-11-15 · D6 · Inference: user-clustered bootstrap plus user fixed-effects regression
- Alternatives: bootstrap only; off-policy evaluation.
- Reason: two independent estimates guard against one method's quirks. Off-policy evaluation would
  pull the project toward recommender research.

## 2026-11-15 · D5 · Dashboard never queries BigQuery
- Reason: zero running cost, fast pages, no exposed credentials. Raw tables can be dropped after the
  project without breaking the demo.

## 2026-11-15 · D4 · BigQuery + dbt on KuaiRand-27K
- Alternatives: DuckDB locally; KuaiRand-1K only.
- Reason: 27K gives 300M+ impressions and enough users per segment. BigQuery and dbt match the stack
  of the target employers. Expected cost: under $3 total with the controls in CLAUDE.md.

## 2026-11-15 · D3 · Segments from pre-period data only
- Reason: segment membership cannot be affected by the treatment window.

## 2026-11-15 · D2 · One pre-registered primary metric, duration-adjusted
- Reason: completion rate favors short videos and watch time favors long ones; a naive metric can
  reverse the conclusion.

## 2026-11-15 · D1 · Main question: exploration budget by segment
- Alternatives: "how much better is recommendation than random" alone; "which metric should the feed
  optimize" alone.
- Reason: the budget question forces a decision. The other two become components
  (Comparison A and the metric framework).
