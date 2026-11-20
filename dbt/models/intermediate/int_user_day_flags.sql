{{ config(cluster_by=['user_id']) }}

-- D20/D42: exposures per user-day over both logs, all tabs, 2022-04-08 to 05-08. The top 0.1% of
-- user-days (count above the exact p99.9, D50) are flagged for the sensitivity run.
with user_days as (
    select user_id, event_date, count(*) as n_exposures
    from {{ ref('int_exposures') }}
    group by user_id, event_date
),

value_counts as (
    select n_exposures, count(*) as n_user_days
    from user_days
    group by n_exposures
),

cumulative as (
    select
        n_exposures,
        sum(n_user_days) over (order by n_exposures) as cum_n,
        sum(n_user_days) over () as total_n
    from value_counts
),

threshold as (
    select min(if(cum_n * 1000 >= 999 * total_n, n_exposures, null)) as p999
    from cumulative
)

select
    {{ dbt_utils.generate_surrogate_key(['d.user_id', 'd.event_date']) }} as user_day_key,
    d.user_id,
    d.event_date,
    d.n_exposures,
    t.p999 as p999_threshold,
    d.n_exposures > t.p999 as is_top_user_day
from user_days as d
cross join threshold as t
