# CLAUDE.md

## What this project is
A decision analysis: how much of a short-video feed should go to exploration, and for which users.
It uses KuaiRand-27K, where some recommended videos were replaced at random. Each random slot is a
measured exploration slot. Full plan: `docs/design.md`. Locked metrics and parameters: `docs/analysis_plan.md`.

## Locked decisions (do not change without a new entry in docs/decisions.md)
- Primary metric: duration-adjusted effective view rate, defined in `docs/analysis_plan.md`.
- Three comparisons: A (random vs recommended, within user), B (same pool video, recommended vs random),
  C (total gap = content gap + targeting gap).
- Segments come from pre-period data only (2022-04-08 to 04-21). The pre-period never measures effects.
- Inference: user-clustered bootstrap (fixed seed, >= 2,000 resamples) cross-checked with a user
  fixed-effects regression, SEs clustered by user. Segment results use Benjamini-Hochberg.
- No effect query (random vs recommended outcomes) runs before the health checks in
  `docs/design.md` pass and `docs/analysis_plan.md` is tagged `prereg-v1`.

## Non-goals
- Do not train or tune any recommendation model. Every analysis must map to the exploration decision.
- No live BigQuery queries from the dashboard. It reads static files in `exports/`.

## Cost rules (BigQuery, on-demand billing)
- Work on the dbt `dev` target (5% hashed user sample) by default. Run `prod` only when asked.
- Every query and dbt profile sets `maximum_bytes_billed`. Dry-run (`--dry_run`) anything new on full tables.
- Never `SELECT *` on raw log tables. Raw logs are partitioned by date and clustered by user_id, is_rand.
- Ask before any operation estimated to scan more than 50 GB.

## Conventions
- dbt layers: `stg_` (types, renames, dedupe) -> `int_` -> `fct_` / `dim_` / `mart_`. One model per file.
- Every model has a YAML entry with a description and tests (keys: unique + not_null at minimum).
- SQL: lowercase keywords, CTEs over subqueries, explicit column lists.
- Python: pinned versions, fixed random seeds, no notebooks as the only record of a result.
- Every number that reaches the README, memo or dashboard comes from a committed query or script.
- Data-quality findings go in `docs/data_quality.md`; plan changes go in `docs/decisions.md`.

## Workflow
- One phase per branch and PR. Propose a plan first, implement after approval.
- Never commit data, credentials, or `profiles.yml`.

## Git authorship (owner's rule)
- Hanson Yang is the author and committer of every commit. Use the repo's git config as is; never
  set Claude, a bot, or any other name or email as author or committer.
- Claude is credited only as a co-author, with this trailer at the end of the message:
  `Co-Authored-By: Claude <noreply@anthropic.com>`
- Commit small and often: one logical change per commit (a model, its tests, a script, a doc update),
  each message saying why. Push after each completed step, not once at the end of a phase.
- PRs merge with "Create a merge commit" or "Rebase and merge", never "Squash and merge", so every
  commit stays in the history.

## Data and license
KuaiRand (CC BY-SA 4.0): https://kuairand.com/ and https://arxiv.org/abs/2208.08696.
Attribute in the README. Exported derived data in `exports/` is shared under CC BY-SA 4.0.
Public data only: never use or reference any TikTok internal information.
