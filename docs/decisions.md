# Decision Log

Each entry: date, decision, alternatives considered, reason. Newest first.

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
