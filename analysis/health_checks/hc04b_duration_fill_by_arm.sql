-- scope: dev5
-- HC 4b (D19): missing duration before and after filling duration_ms from
-- video_features_basic.video_duration, by is_rand, in the analysis population (tab 1, treatment
-- window). Missing duration is a data property of the exposure, not an outcome.
with exposures as (
    select video_id, duration_ms, is_rand
    from {treat}
    where event_date between '2022-04-22' and '2022-05-08' and tab = 1
    union all
    select video_id, duration_ms, is_rand
    from {rnd}
    where event_date between '2022-04-22' and '2022-05-08' and tab = 1
),

filled as (
    select
        e.is_rand,
        e.duration_ms is null or e.duration_ms <= 0 as log_missing,
        coalesce(
            if(e.duration_ms > 0, e.duration_ms, null),
            if(v.video_duration > 0, v.video_duration, null)
        ) is null as still_missing
    from exposures as e
    left join {raw}.video_features_basic as v on e.video_id = v.video_id
)

select
    is_rand,
    count(*) as n_rows,
    countif(log_missing) as n_log_missing,
    countif(still_missing) as n_still_missing
from filled
group by is_rand
order by is_rand
