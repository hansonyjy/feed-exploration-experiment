-- scope: dev5
-- HC 4c (post-hoc, D23): profile tab-1 rows whose duration is still missing after the fill from
-- video_features_basic, by arm, video_type and upload period. Counts only. Window 2022-04-23 to 05-08.
with exposures as (
    select 'recommended' as arm, video_id, duration_ms
    from {treat}
    where event_date between '2022-04-23' and '2022-05-08' and tab = 1
    union all
    select 'random' as arm, video_id, duration_ms
    from {rnd}
    where event_date between '2022-04-23' and '2022-05-08' and tab = 1
),

labeled as (
    select
        e.arm,
        e.video_id,
        coalesce(if(e.duration_ms > 0, e.duration_ms, null), if(v.video_duration > 0, v.video_duration, null)) is null
            as is_missing,
        coalesce(v.video_type, 'no_features') as video_type,
        case
            when v.upload_dt is null then 'no_upload_date'
            when v.upload_dt < '2022-03-01' then 'a_before_2022-03'
            when v.upload_dt < '2022-04-08' then 'b_2022-03-01_to_04-07'
            when v.upload_dt < '2022-04-22' then 'c_pre_period_04-08_to_04-21'
            else 'd_treatment_04-22_to_05-08'
        end as upload_period
    from exposures as e
    left join {raw}.video_features_basic as v on e.video_id = v.video_id
),

video_missing as (
    select video_id, logical_and(is_missing) as always_missing
    from labeled
    group by video_id
)

select
    l.arm,
    l.is_missing,
    l.video_type,
    l.upload_period,
    count(*) as n_rows,
    count(distinct l.video_id) as n_videos,
    countif(vm.always_missing) as n_rows_video_always_missing
from labeled as l
inner join video_missing as vm on l.video_id = vm.video_id
group by l.arm, l.is_missing, l.video_type, l.upload_period
order by l.arm, l.is_missing, l.video_type, l.upload_period
