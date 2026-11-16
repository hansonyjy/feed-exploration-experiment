-- scope: dev5
-- HC 2b: attributes of pool videos (all videos in the random log) vs all videos exposed by the
-- standard log in the dev sample. Video attributes only, no outcomes.
with pool as (
    select distinct video_id
    from {rnd_full}
    where event_date between '2022-04-22' and '2022-05-08'
),

standard_exposed as (
    select distinct video_id
    from {treat}
    where event_date between '2022-04-22' and '2022-05-08'
),

sets as (
    select 'pool' as video_set, video_id from pool
    union all
    select 'standard_exposed_dev5' as video_set, video_id from standard_exposed
)

select
    s.video_set,
    count(*) as n_videos,
    countif(v.video_id is null) as n_missing_features,
    countif(v.video_type = 'NORMAL') / count(*) as share_normal,
    countif(v.video_type = 'AD') / count(*) as share_ad,
    approx_quantiles(v.video_duration, 10) as duration_ms_deciles,
    min(v.upload_dt) as min_upload_dt,
    max(v.upload_dt) as max_upload_dt,
    countif(v.upload_dt >= '2022-04-08') / count(*) as share_uploaded_in_window
from sets as s
left join {raw}.video_features_basic as v on s.video_id = v.video_id
group by s.video_set
order by s.video_set
