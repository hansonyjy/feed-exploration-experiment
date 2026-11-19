-- D26 duration buckets: deciles of filled duration over tab-1 pre-period recommended impressions with a
-- valid duration. Exact quantiles (D50): edge k is the smallest duration whose cumulative count reaches
-- k/10 of the rows; a duration equal to an edge falls in the lower bucket. Buckets 1 and 10 are
-- open-ended. Kept for audit: the full-data result was exported once to the frozen_duration_buckets seed
-- (scripts/freeze_reference.py, D55), which int_duration_buckets reads on every target.
with reference_rows as (
    select duration_filled_ms
    from {{ ref('int_exposures') }}
    where period = 'pre'
        and event_date between '{{ var("pre_start") }}' and '{{ var("pre_end") }}'
        and tab = 1
        and is_rand = 0
        and has_valid_duration
),

value_counts as (
    select duration_filled_ms, count(*) as n
    from reference_rows
    group by duration_filled_ms
),

cumulative as (
    select
        duration_filled_ms,
        sum(n) over (order by duration_filled_ms) as cum_n,
        sum(n) over () as total_n
    from value_counts
),

edges as (
    select
        k,
        min(if(c.cum_n * 10 >= k * c.total_n, c.duration_filled_ms, null)) as edge_ms
    from cumulative as c
    cross join unnest(generate_array(1, 9)) as k
    group by k
),

buckets as (
    select
        bucket,
        (select edge_ms from edges where k = bucket - 1) as lower_exclusive_ms,
        (select edge_ms from edges where k = bucket) as upper_inclusive_ms
    from unnest(generate_array(1, 10)) as bucket
)

select
    bucket as duration_bucket,
    lower_exclusive_ms,
    upper_inclusive_ms,
    (select max(total_n) from cumulative) as n_reference_rows
from buckets
