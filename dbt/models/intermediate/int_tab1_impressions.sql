{{
    config(
        partition_by={'field': 'event_date', 'data_type': 'date', 'granularity': 'day'},
        cluster_by=['request_key', 'user_id']
    )
}}

-- The analysis population (D15, D22): tab-1 exposures from 2022-04-23 to 05-08, both arms, with the
-- request they belong to, regime (D17), D26 bucket, first-level category and pool flags. No outcome
-- logic here; metrics are computed in fct_tab1_impression_metrics.
with tab1 as (
    select
        exposure_key, request_key, user_id, video_id, author_id, event_date, event_hour, time_ms,
        is_rand, is_click, is_like, is_follow, is_comment, is_forward, is_hate, is_profile_enter,
        play_time_ms, duration_filled_ms, has_valid_duration
    from {{ ref('int_exposures') }}
    where tab = 1
        and period = 'treatment'
        and event_date between '{{ var("analysis_start") }}' and '{{ var("treat_end") }}'
),

request_sizes as (
    select request_key, count(*) as n_items, sum(is_rand) as n_random_items
    from tab1
    group by request_key
)

select
    t.exposure_key,
    t.request_key,
    t.user_id,
    t.video_id,
    t.author_id,
    t.event_date,
    case
        when t.event_date < '{{ var("transition_date") }}' then 'low'
        when t.event_date = '{{ var("transition_date") }}' then 'transition'
        else 'high'
    end as regime,
    t.event_hour,
    t.time_ms,
    t.is_rand,
    rs.n_items as request_n_items,
    rs.n_random_items > 0 as request_has_random,
    t.is_click,
    t.is_like,
    t.is_follow,
    t.is_comment,
    t.is_forward,
    t.is_hate,
    t.is_profile_enter,
    t.play_time_ms,
    t.duration_filled_ms,
    t.has_valid_duration,
    b.duration_bucket,
    c.category_l1_id,
    pv.video_id is not null as is_pool_video,
    coalesce(pv.is_ad, false) as is_ad_pool_video
from tab1 as t
inner join request_sizes as rs on t.request_key = rs.request_key
left join {{ ref('int_duration_buckets') }} as b
    on t.has_valid_duration and {{ duration_bucket_join('t.duration_filled_ms', 'b') }}
left join {{ ref('stg_video_categories') }} as c on t.video_id = c.final_video_id
left join {{ ref('int_pool_videos') }} as pv on t.video_id = pv.video_id
