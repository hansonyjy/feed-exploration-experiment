# Exploration budget for the short-video feed

Decision memo · Hanson Yang · December 2026

## Recommendation

1. **Exploration up to 1.388% of the feed is safe to keep.** No guardrail was crossed at that share, the highest in the data, and it costs 4.8 effective views per 1,000 impressions. Its payoff is long-run and was not measured here.
2. **Keep dance videos out of the random pool.** They are the only content where hate clearly passes its limit.
3. **Next, test 2-3% targeted exploration.** Most of what exploration costs comes from who sees the video, not the video.

## Context

KuaiRand is a public dataset of viewing logs from Kuaishou, a large short-video app. For a small share of feed requests, the app swapped one recommended video for a random one, so each random slot is a measured exploration slot (26,955 users and 1,081,088 random requests, April 23 to May 8, 2022).

## What we found

- **A random slot costs 34.6 pp of effective views (−63%).** An effective view is one at least as long as the typical view of a video of similar length. Recommended slots get 54.8%.
- **94% of that gap is targeting, not content.** When the random pool's videos are recommended, they do almost as well as other recommended videos: the content part is 2.1 pp and the targeting part 33.6 pp.
- **Costs vary more by content than by user.** Random gaming videos cost 42.2 pp and comedy 28.3 pp. User groups differ by a few points.
- **Guardrails hold for the whole feed but not for dance.** At 1.388%, hate rises 1.60% and fast skip 1.32%, both under the 2% limit. Dance videos push hate past the limit even at 0.658%, the lowest share in the data (+3.3%).

## What we don't know

- **Anything above 1.388%.** No higher share was observed, so the data cannot say how far exploration could go. That needs a new test.
- **Whether exploration pays off later.** Random slots also give fewer new-category effective views (1.21% vs 1.76% of impressions), so the short-run data shows no discovery benefit. The case for exploration rests on long-run effects, such as users finding new interests and the recommender learning from them. A 16-day window cannot measure those.
- **Before vs after May Day.** The insertion rate rose in early May, around the holiday, so the two periods are never compared. Every comparison is within the same feed request or day.
- **Session exits.** Whether random slots end sessions early cannot be identified from these logs (decision D53).
- **Other apps and years.** This is one app, in 2022.

## Next experiment

Randomize by user, not by slot, for about four weeks. Four arms, with dance videos excluded from the random pool in all of them:

| Arm | Exploration share | Pool videos chosen |
|---|---|---|
| Control | 1.388% | at random (current policy) |
| Random 2% | 2% | at random |
| Targeted 2% | 2% | matched to the user's interests |
| Targeted 3% | 3% | matched to the user's interests |

Random 2% vs targeted 2% measures what targeting saves; targeted 2% vs targeted 3% measures how far the share can go.

- **Primary metric:** effective views per impression.
- **Guardrails:** hate and fast skip, each limited to a 2% relative worsening of the feed, as in this analysis.
- **Long-run metrics:** 14-day retention, first-week views of creators new to the user, and new categories still watched after two weeks.
- **Sample size:** minimum detectable effects need a power analysis for this design. No committed script computes them yet.

Pre-register metrics and limits before launch, as here.

## Links

- Dashboard: <https://hansonyjy.github.io/feed-exploration-experiment/>
- Findings: [docs/findings.md](findings.md)
- Decision log: [docs/decisions.md](decisions.md)
- Pre-registered plan: [docs/analysis_plan.md](analysis_plan.md), tag `prereg-v1`
