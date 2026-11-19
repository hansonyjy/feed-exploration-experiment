{{
    config(
        partition_by={'field': 'event_date', 'data_type': 'date', 'granularity': 'day'},
        cluster_by=['request_key', 'user_id']
    )
}}

-- One row per tab-1 impression in the analysis window with every pre-registered metric (analysis_plan.md)
-- and the flags for robustness and sensitivity runs. Duration-based metrics are null without a valid
-- duration (D23, D51). Session exit is per request and joined from int_sessions (D35-D38).
with impressions as (
    select
        exposure_key, request_key, user_id, video_id, author_id, event_date, regime, event_hour, is_rand,
        request_n_items, request_has_random, is_like, is_follow, is_comment, is_forward, is_hate,
        is_profile_enter, play_time_ms, duration_filled_ms, has_valid_duration, duration_bucket,
        category_l1_id, is_pool_video, is_ad_pool_video
    from {{ ref('int_tab1_impressions') }}
),

labeled as (
    select
        i.*,
        r.median_play_time_ms,
        ah.author_id is null and i.author_id is not null as is_new_author,
        ch.category_l1_id is null and i.category_l1_id is not null as is_new_category,
        coalesce(ud.is_top_user_day, false) as is_top_user_day,
        s.is_session_exit_within_3,
        s.is_censored
    from impressions as i
    left join {{ ref('int_reference_thresholds') }} as r on i.duration_bucket = r.duration_bucket
    left join {{ ref('int_user_author_history') }} as ah
        on i.user_id = ah.user_id and i.author_id = ah.author_id
    left join {{ ref('int_user_category_history') }} as ch
        on i.user_id = ch.user_id and i.category_l1_id = ch.category_l1_id
    left join {{ ref('int_user_day_flags') }} as ud
        on i.user_id = ud.user_id and i.event_date = ud.event_date
    left join {{ ref('int_sessions') }} as s on i.request_key = s.request_key
)

select
    exposure_key,
    request_key,
    user_id,
    video_id,
    event_date,
    regime,
    event_hour,
    is_rand,
    request_n_items,
    request_has_random,
    has_valid_duration,
    duration_bucket,
    is_pool_video,
    is_ad_pool_video,
    is_top_user_day,
    is_censored,
    -- primary metric (D25, D26, D29)
    if(has_valid_duration, if(play_time_ms >= median_play_time_ms, 1, 0), null) as effective_view,
    -- secondary
    if(has_valid_duration, if(play_time_ms >= duration_filled_ms, 1, 0), null) as naive_completion,
    cast(play_time_ms as float64) as watch_time_ms,
    is_like as like_,
    is_comment as comment_,
    is_forward as forward_,
    is_profile_enter as profile_enter,
    -- discovery (D32-D34)
    if(is_follow = 1 and is_new_author, 1, 0) as new_author_follow,
    if(
        has_valid_duration,
        if(play_time_ms >= median_play_time_ms and is_new_category, 1, 0),
        null
    ) as new_category_effective_view,
    -- guardrails
    is_hate as hate,
    if(play_time_ms < 3000, 1, 0) as fast_skip,
    if(is_censored, null, if(is_session_exit_within_3, 1, 0)) as session_exit_request
from labeled
