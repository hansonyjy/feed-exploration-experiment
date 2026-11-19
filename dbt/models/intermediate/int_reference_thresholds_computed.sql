-- D25/D29/D30 effective-view thresholds: per D26 bucket, the median play_time_ms of tab-1 pre-period
-- recommended impressions with a valid duration (deduplicated staging rows). Exact median (D50): the
-- smallest play time whose cumulative count reaches half the bucket's rows. An effective view is
-- play_time_ms >= this value. Kept for audit: the full-data result was exported once to the
-- frozen_reference_thresholds seed (D55), which int_reference_thresholds reads on every target.
with reference_rows as (
    select e.play_time_ms, b.duration_bucket
    from {{ ref('int_exposures') }} as e
    inner join {{ ref('int_duration_buckets_computed') }} as b
        on {{ duration_bucket_join('e.duration_filled_ms', 'b') }}
    where e.period = 'pre'
        and e.event_date between '{{ var("pre_start") }}' and '{{ var("pre_end") }}'
        and e.tab = 1
        and e.is_rand = 0
        and e.has_valid_duration
),

value_counts as (
    select duration_bucket, play_time_ms, count(*) as n
    from reference_rows
    group by duration_bucket, play_time_ms
),

cumulative as (
    select
        duration_bucket,
        play_time_ms,
        sum(n) over (partition by duration_bucket order by play_time_ms) as cum_n,
        sum(n) over (partition by duration_bucket) as total_n
    from value_counts
)

select
    duration_bucket,
    min(if(cum_n * 2 >= total_n, play_time_ms, null)) as median_play_time_ms,
    max(total_n) as n_reference_rows
from cumulative
group by duration_bucket
