{{
    config(
        partition_by={'field': 'event_date', 'data_type': 'date', 'granularity': 'day'},
        cluster_by=['user_id', 'video_id']
    )
}}

-- Every exposure from both logs, all tabs, 2022-04-08 to 05-08 (sessions, history, profiles and the
-- tab-1 analysis rows all start here). Adds the filled duration (D19, D23) and the video's author.
-- impression_id is not unique (HC 5 key conflicts), so the key hashes every source column.
with exposures as (
    select
        source_table, period, user_id, video_id, event_date, hour_min, event_hour, time_ms, is_click,
        is_like, is_follow, is_comment, is_forward, is_hate, is_long_view, is_profile_enter,
        play_time_ms, duration_ms, profile_stay_time, comment_stay_time, is_rand, tab
    from {{ ref('stg_log_standard') }}
    union all
    select
        source_table, period, user_id, video_id, event_date, hour_min, event_hour, time_ms, is_click,
        is_like, is_follow, is_comment, is_forward, is_hate, is_long_view, is_profile_enter,
        play_time_ms, duration_ms, profile_stay_time, comment_stay_time, is_rand, tab
    from {{ ref('stg_log_random') }}
),

videos as (
    select video_id, author_id, video_duration_ms
    from {{ ref('stg_videos') }}
)

select
    {{ dbt_utils.generate_surrogate_key([
        'e.source_table', 'e.user_id', 'e.video_id', 'e.event_date', 'e.hour_min', 'e.time_ms',
        'e.is_click', 'e.is_like', 'e.is_follow', 'e.is_comment', 'e.is_forward', 'e.is_hate',
        'e.is_long_view', 'e.is_profile_enter', 'e.play_time_ms', 'e.duration_ms',
        'e.profile_stay_time', 'e.comment_stay_time', 'e.is_rand', 'e.tab'
    ]) }} as exposure_key,
    {{ dbt_utils.generate_surrogate_key(['e.user_id', 'e.time_ms']) }} as request_key,
    e.source_table,
    e.period,
    e.user_id,
    e.video_id,
    v.author_id,
    e.event_date,
    e.event_hour,
    e.time_ms,
    e.tab,
    e.is_rand,
    e.is_click,
    e.is_like,
    e.is_follow,
    e.is_comment,
    e.is_forward,
    e.is_hate,
    e.is_long_view,
    e.is_profile_enter,
    e.play_time_ms,
    e.duration_ms,
    case
        when e.duration_ms > 0 then cast(e.duration_ms as float64)
        when v.video_duration_ms > 0 then v.video_duration_ms
    end as duration_filled_ms,
    coalesce(e.duration_ms > 0 or v.video_duration_ms > 0, false) as has_valid_duration
from exposures as e
left join videos as v on e.video_id = v.video_id
