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
Guardrail limit: _proposed_ no guardrail metric worsens by more than 2% relative at the feed level.
Interpolate only within observed random-insertion rates.
