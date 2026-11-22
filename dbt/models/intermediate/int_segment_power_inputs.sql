-- Minimum-detectable-effect inputs (D39, D58), pre-period only: no treatment outcomes. For each tab-1
-- pre-period request (2022-04-08 to 04-21) with at least two recommended items with a valid duration,
-- one item is picked by a fixed hash (a placebo "random slot") and the within-request difference
-- d = effective view of that item minus the mean of the others is formed, mirroring Comparison A's
-- within-request design. One row per user: counts and sums that give the variance of d and its
-- within-user correlation, plus the user's pre-period effective-view rate.
with reference_items as (
    select
        e.user_id,
        e.time_ms,
        e.video_id,
        if(e.play_time_ms >= r.median_play_time_ms, 1, 0) as effective_view
    from {{ ref('int_exposures') }} as e
    inner join {{ ref('int_duration_buckets') }} as b
        on {{ duration_bucket_join('e.duration_filled_ms', 'b') }}
    inner join {{ ref('int_reference_thresholds') }} as r
        on b.duration_bucket = r.duration_bucket
    where e.period = 'pre'
        and e.event_date between '{{ var("pre_start") }}' and '{{ var("pre_end") }}'
        and e.tab = 1
        and e.is_rand = 0
        and e.has_valid_duration
),

ranked as (
    select
        user_id,
        time_ms,
        effective_view,
        row_number() over (
            partition by user_id, time_ms
            order by farm_fingerprint(format('%d-%d-%d', user_id, time_ms, video_id)), video_id
        ) as pick_rank,
        count(*) over (partition by user_id, time_ms) as n_in_request,
        sum(effective_view) over (partition by user_id, time_ms) as sum_in_request
    from reference_items
),

placebo as (
    select
        user_id,
        effective_view - (sum_in_request - effective_view) / (n_in_request - 1) as d
    from ranked
    where pick_rank = 1 and n_in_request >= 2
),

user_rates as (
    select user_id, count(*) as n_reference_items, sum(effective_view) as n_effective_views
    from reference_items
    group by user_id
),

user_placebo as (
    select user_id, count(*) as n_placebo_requests, sum(d) as sum_d, sum(d * d) as sum_d2
    from placebo
    group by user_id
)

select
    u.user_id,
    u.n_reference_items,
    u.n_effective_views,
    coalesce(p.n_placebo_requests, 0) as n_placebo_requests,
    coalesce(p.sum_d, 0) as sum_d,
    coalesce(p.sum_d2, 0) as sum_d2
from user_rates as u
left join user_placebo as p on u.user_id = p.user_id
