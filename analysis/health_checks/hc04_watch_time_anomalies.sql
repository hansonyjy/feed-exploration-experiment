-- scope: dev5
-- HC 4: watch-time and duration anomalies, by period only. Standard and random rows are pooled within
-- each period and never split by source or is_rand (CLAUDE.md lock on outcome comparisons).
with exposures as (
    select 'pre' as period, video_id, play_time_ms, duration_ms
    from {pre} where event_date between '2022-04-08' and '2022-04-21'
    union all
    select 'treatment', video_id, play_time_ms, duration_ms
    from {treat} where event_date between '2022-04-22' and '2022-05-08'
    union all
    select 'treatment', video_id, play_time_ms, duration_ms
    from {rnd} where event_date between '2022-04-22' and '2022-05-08'
)

select
    e.period,
    count(*) as n_rows,
    countif(e.duration_ms is null or e.duration_ms <= 0) as n_bad_duration,
    countif(e.play_time_ms is null) as n_null_play,
    countif(e.play_time_ms < 0) as n_negative_play,
    countif(e.duration_ms > 0 and e.play_time_ms > 5 * e.duration_ms) as n_play_over_5x,
    countif(v.video_id is not null) as n_with_video_features,
    countif(v.video_id is not null and abs(e.duration_ms - v.video_duration) <= 1000) as n_duration_within_1s
from exposures as e
left join {raw}.video_features_basic as v on e.video_id = v.video_id
group by e.period
order by e.period
