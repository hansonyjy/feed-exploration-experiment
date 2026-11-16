# Decision Log

Each entry: date, decision, alternatives considered, reason. Newest first.

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
