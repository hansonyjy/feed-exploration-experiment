# Data Quality Log

One entry per check. Status: open, handled, or accepted with a stated impact.

| # | Check | Finding | Handling | Impact on results | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Sample ratio: random share by day, tab, segment | Overall 0.634% (full data). The insertion rate changes mid-window: 0.41-0.50% on 04-23 to 05-01, 0.70% on 05-02, 0.91-0.99% on 05-03 to 05-08; 04-22 is 0.25%. 99.3% of random rows are on tab 1 (0.93% of tab-1 exposures); tabs 0, 3-10, 12 and 13 have none. Segment deviations: pre-activity tercile 1 +108%, tercile 3 -36%; middle_active and high_active +27%; tenure 61-90 +29%. FAIL on day, tercile, active group and tenure (blocking); tab non-blocking | Pending a design decision. Likely cause is structural: two insertion regimes by date, insertion on tab 1 only, and segments differing in tab and day mix. Proposed re-check: stability within tab 1 and within each date regime | Blocks Phase 1. Comparison A must be within day (or regime) and tab; the budget can only interpolate between the two observed rates | open (blocking) |
| 2 | Random items match the paper's pool description | 7,583 pool videos; exposures per video CV 0.197 (pass), but min 1 / max 214 (max/min fails). All pool videos were uploaded 2022-04-09 to 04-11; median duration 81 s vs 34 s for standard-exposed videos (dev); AD share 1.0% vs 0.24% | Report pool composition with Comparison C | Pool content is systematically newer and longer than recommended content, so the content gap in C is real and the duration adjustment (D2) is essential | open |
| 3 | Treatment-window users found in the pre-period | 98.24% of treatment users have pre-period exposures; 100% of random-log users also have standard exposures (dev). PASS | None needed | Within-user comparison and pre-period segments are available for nearly all users | handled |
| 4 | Watch-time anomalies: loops, zero or missing duration | Null or non-positive duration_ms on 8.71% (pre) and 8.64% (treatment) of rows; log duration within 1 s of the feature table for 91.3%; play > 5x duration 0.29% / 0.27%; no negative play times (dev). FAIL on bad duration and duration agreement | Handling rule needed before metrics: which duration source to use and how to treat the 8.7% of rows without one | Directly affects the primary metric's duration buckets | open |
| 5 | Exact duplicate rows, repeated impressions | Raw, dev sample: exact duplicates 0.65% (pre), 0.87% (treat), 0.002% (random); key conflicts 0.098% (pre), 0.123% (treat), 0 (random). FAIL on exact duplicates (pre, treat) and treat key conflicts | D13 (collapse exact duplicates) still applies; conflicting rows kept. impression_id uniqueness stays warn-level | About 0.8% of standard rows removed in staging | open |
| 6 | Extreme users (possible bots or test accounts) | Exposures per user-day: p50 269, p99 2,521, p99.9 5,495, max 11,158 (dev). 13.7% of users and 36.5% of exposures flagged. FAIL | The 2,000/day bar sits below the user-day p99, so it does not isolate outliers in this log (rows are exposures, not views). Criterion needs re-calibration | Non-blocking; affects only the planned sensitivity check | open |
| 7 | Tabs that carry random insertions | Tab 1: 1,178,025 (99.3%); tab 11: 6,755 (0.6%); tab 2: 764 (0.1%); tab 14: 515 (0.04%) (full data) | Documented | Random-vs-recommended comparisons are effectively tab-1 comparisons | handled |
| 8 | How the 7,583-video candidate pool was selected | | | | open |
| 9 | Random exposures also present in the standard log | is_rand = 0 on all 322.3M standard rows. 0 of 1,186,049 random keys appear in the standard treatment log, but 1,150,410 (97.0%) share user and time_ms with standard rows (full data). PASS | None. The random log holds the inserted items; the standard log holds the rest of the same feed request. is_rand = 0 test now error-level | No double counting; random and standard rows are separate exposures, mostly from shared requests | handled |
| 10 | Dates and timestamps: event_date vs time_ms, window bounds | All windows match exactly. event_date equals the Shanghai date of time_ms for 99.24-99.31% of rows (UTC 83-85%); hourmin is always on the hour and matches the Shanghai hour for 82-83% (dev). FAIL on the 99.9% date bar (non-blocking) | Use event_date and hourmin as provided; derive sessions from time_ms | Minor | open |
| 11 | Feature and category coverage of logged users and videos | 100% of log users and videos found in the feature tables; 100% of treatment videos found in the category file. First-level category id appears in the tag ids for 74.6% of 3.2M videos (dev). FAIL on the 90% bar | final_video_id is very likely video_id (full coverage; 75% agreement is far above chance), but tag and category taxonomies do not align fully | Category segments usable with a stated caveat | open |
| 12 | Domain values of categorical features (found by staging tests, 2026-11-16) | `user_active_degree` has 8 levels, not the 3 the site lists: full 17,959, high 6,158, middle 2,133, 2_14_day_new 635, low 300, single_low 68, 30day_retention 15, day_new 11, UNKNOWN 6. `video_type` has 1,899 UNKNOWN among 32.0M videos | Staging accepts all 8 levels; UNKNOWN becomes null in both columns | The small new and low-activity levels must be merged before segment analysis (minimum-detectable-effect rule in the analysis plan) | handled |

Results: `exports/health/` (from `scripts/run_health_checks.py`, run 2026-11-16; 23.1 GB billed).

## Pass criteria (approved 2026-11-16, before any check ran)

Written before any check runs. A **blocking** failure stops Phase 1 until the design is adjusted and
the change is logged in `docs/decisions.md`. A **non-blocking** failure is recorded above with a
handling rule and its impact. With hundreds of millions of rows every significance test rejects, so
the thresholds are practical tolerances, not p-values.

Rule for every check: no query groups an outcome column (watch time, likes, hates, follows and so on)
by `is_rand`. Only exposure counts and video attributes are split by arm. HC 4 reports anomaly rates
by period only.

| # | Pass criterion | Severity | Data |
| --- | --- | --- | --- |
| 1 | Random share = random / (random + standard) exposures in the treatment window. No absolute band: the "about 0.37%" on kuairand.com (dataset site, not the paper) equals random rows over all standard rows in both windows (1,186,059 / 322,278,385 = 0.368%); the treatment-window share from the loaded counts is 0.634%. Each day's and each segment's share (pre-period activity tercile, `user_active_degree` merged groups per analysis_plan.md, tenure band) within ±20% (relative) of the overall share. Tabs: reported, share within ±50%. Only cells with at least 1,000 expected random exposures (cell exposures × overall share) are judged; smaller cells are reported only | Blocking for day and segment; tab is non-blocking | full data (counts only) |
| 2 | Distinct random videos between 7,500 and 7,583. Per-video exposure counts have a coefficient of variation ≤ 0.25 (uniform draws give about 0.08) and max/min ratio ≤ 3. Pool video type and duration distributions are reported against all exposed videos | Non-blocking. A non-uniform pool changes the weighting in Comparisons B and C, not the validity of A | full random log (about 1.19M rows) |
| 3 | ≥ 95% of treatment-window users have at least one pre-period exposure. ≥ 99% of random-log users also have standard treatment exposures | Blocking below 80% (segments need pre-period history); between 80% and 95%, non-blocking with a stated impact | dev sample |
| 4 | Null, zero or negative `duration_ms` ≤ 0.5% of rows. Negative `play_time_ms`: 0 rows. `play_time_ms` > 5 × `duration_ms` ≤ 1% of rows. Log `duration_ms` within 1 s of `video_duration` for ≥ 99% of rows | Non-blocking. A handling rule is set before metrics are built (for example, exclude zero-duration rows from duration buckets) | dev sample |
| 5 | On raw tables, before staging dedupes: exact duplicate rows ≤ 0.1% of rows, and rows that share (user, video, `time_ms`) but differ in other columns ≤ 0.1% | Above 0.1%, non-blocking but the dedupe rule (D13) and the impression key are revisited. Once this passes, the `impression_id` uniqueness test goes from warn to error | raw dev5 tables |
| 6 | Users whose busiest day exceeds 2,000 exposures, or whose daily count is above the user-day p99.9: ≤ 0.5% of users and ≤ 2% of exposures | Non-blocking. Flagged users stay in the main analysis and are excluded in a sensitivity check | dev sample |
| 7 | Random rows by tab are reported; documented, no threshold | Non-blocking. Informs the tab controls in the regression | dev sample |
| 8 | Pool selection documented from the KuaiRand paper; no query | Non-blocking | paper |
| 9 | `is_rand` = 0 for every standard-log row. The overlap of (user, video, `time_ms`) between the random log and the standard treatment log is either about 0% or about 100% of random rows (a clear structure either way) | Blocking if the overlap is partial or unexplained (Comparison A could double count). Once this passes, the `is_rand` = 0 test goes from warn to error | full data (counts only) |
| 10 | Each table's `event_date` range matches its file window exactly. `event_date` equals the date of `time_ms` in Asia/Shanghai time for ≥ 99.9% of rows | Blocking for a window mismatch; non-blocking for the timestamp check | dev sample |
| 11 | ≥ 99.9% of logged users found in `user_features`. ≥ 99% of logged videos found in `video_features_basic`. ≥ 95% of treatment-log videos found in the category file by `final_video_id`, and for ≥ 90% of matched videos the first-level category id appears in the 27K `tag` ids (a check that `final_video_id` is the 27K `video_id`) | Blocking for users. Non-blocking for videos and categories: below threshold, category segments and the new-category metric are dropped or redesigned | dev sample + full video tables |

## Re-specified criteria (post-hoc, approved 2026-11-16 after the first run, before any outcome query)

Logged as D16 and D20 in `docs/decisions.md`. The first-run results above stay on record.

| # | Pass criterion | Severity | Data |
| --- | --- | --- | --- |
| 1b | Within tab 1 only. Regimes (D17): low = 2022-04-22 to 05-01, transition = 05-02 (reported, not judged), high = 05-03 to 05-08. Within each judged regime, each day's and each segment's (activity tercile, merged `user_active_degree` group, tenure band) tab-1 random share within ±20% (relative) of that regime's tab-1 share. Only cells with at least 1,000 expected random exposures are judged | Blocking | full data (counts only) |
| 4b | Missing duration before and after filling `duration_ms` from `video_features_basic.video_duration`, by `is_rand`, in tab 1 of the treatment window; rows still missing are excluded (D19). Reported, no threshold | Info | dev sample |
| 6 | Top 0.1% of user-days by exposure count are flagged; they stay in the main analysis and are excluded in a sensitivity run. Reported, no threshold (replaces the 2,000/day rule) | Info | dev sample |
| 11 | Users ≥ 99.9% and videos ≥ 99% found in the feature tables; ≥ 95% of treatment videos found in the supplementary category file. The tag criterion is dropped; categories come from the supplementary file only | Users blocking; rest non-blocking | dev sample + full video tables |

