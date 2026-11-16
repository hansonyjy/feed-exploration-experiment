# Analysis Plan (pre-registration)

Status: **DRAFT**. Parameters marked _proposed_ may change after the Phase 0 health checks, which look
only at data structure, never at random-vs-recommended outcomes. Once finalized, this file is committed
and tagged `prereg-v1` before any effect query runs. Later changes are logged in `docs/decisions.md`.

## Question
What share of feed impressions should go to exploration, and should that share differ by user segment?

## Windows
| Window | Dates | Use |
| --- | --- | --- |
| Pre-period | 2022-04-08 to 2022-04-21 | Segments, user history, reference distributions. Never measures effects |
| Treatment | 2022-04-22 to 2022-05-08 | Random (`is_rand = 1`) and recommended (`is_rand = 0`) exposures |

## Primary metric (one, locked)
**Duration-adjusted effective view rate**: share of impressions where watch time reaches the
_proposed_ 50th percentile of watch time for videos in the same duration bucket.
- Duration buckets: _proposed_ deciles of `duration_ms`.
- Reference distribution: built from **pre-period recommended impressions only**, then frozen, so the
  threshold cannot depend on treatment-window outcomes of either arm.

## Secondary, discovery and guardrail metrics
| Tier | Metric | Definition |
| --- | --- | --- |
| Secondary | Like, comment, forward, profile-enter rate | `is_like`, `is_comment`, `is_forward`, `is_profile_enter` per impression |
| Secondary | Naive completion rate, naive watch time | Reported next to the primary metric to show length bias |
| Discovery | New-author follow rate | Follow of an author with no interaction in the pre-period |
| Discovery | New-category engagement rate | Effective view in a category with no effective view in the pre-period |
| Guardrail | Hate rate | `is_hate` per impression |
| Guardrail | Fast-skip rate | `play_time_ms` < _proposed_ 3,000 ms |
| Guardrail | Session-exit rate | Session ends within the next _proposed_ N = 3 impressions |

Sessions: consecutive impressions of a user with gaps under _proposed_ 30 minutes (from `time_ms`).

## Comparisons
- **A, impression level:** within-user mean difference, random minus recommended, treatment window.
- **B, same video:** pool videos only (the 7,583 candidates), recommended vs random exposure.
- **C, decomposition:** total gap = content gap (pool vs typical recommended) + targeting gap (B).

## Inference
- User-clustered bootstrap, B = 2,000 resamples, seed = 20261115, 95% percentile intervals.
- Cross-check: OLS with user fixed effects; controls for tab, hour, duration bucket; SEs clustered by user.
- A headline result requires both methods to agree in sign and significance.
- Segments: Benjamini-Hochberg at q = 0.10. Results failing correction are reported as leads.
- Minimum detectable effects are computed per segment before outcomes are read; segments below the
  _proposed_ threshold of 80% power for a 1-point change in the primary metric are merged.

## Segments (pre-period only)
Pre-period activity terciles; tenure (`register_days_range`); `user_active_degree`; follow-count bands;
duration buckets; `video_type` and category.

## Exploration budget
Guardrail limit: _proposed_ no guardrail metric worsens by more than 2% relative at the feed level.
Interpolate only within observed random-insertion rates.
