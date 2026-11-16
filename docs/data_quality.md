# Data Quality Log

One entry per check. Status: open, handled, or accepted with a stated impact.

| # | Check | Finding | Handling | Impact on results | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Sample ratio: random share by day, tab, segment | | | | open |
| 2 | Random items match the paper's pool description | | | | open |
| 3 | Treatment-window users found in the pre-period | | | | open |
| 4 | Watch-time anomalies: loops, zero or missing duration | | | | open |
| 5 | Exact duplicate rows, repeated impressions | | | | open |
| 6 | Extreme users (possible bots or test accounts) | | | | open |
| 7 | Tabs that carry random insertions | | | | open |
| 8 | How the 7,583-video candidate pool was selected | | | | open |
| 9 | Random exposures also present in the standard log | | | | open |
| 10 | Dates and timestamps: event_date vs time_ms, window bounds | | | | open |
| 11 | Feature and category coverage of logged users and videos | | | | open |
| 12 | Domain values of categorical features (found by staging tests, 2026-11-16) | `user_active_degree` has 8 levels, not the 3 the site lists: full 17,959, high 6,158, middle 2,133, 2_14_day_new 635, low 300, single_low 68, 30day_retention 15, day_new 11, UNKNOWN 6. `video_type` has 1,899 UNKNOWN among 32.0M videos | Staging accepts all 8 levels; UNKNOWN becomes null in both columns | The small new and low-activity levels must be merged before segment analysis (minimum-detectable-effect rule in the analysis plan) | handled |

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
