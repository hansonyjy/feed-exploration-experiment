-- One row per user with any exposure in the data: pre-period segments only (D3).
-- Activity tercile (D45): pre-period exposures across all tabs, ntile(3) over users with any;
-- users with none are no_pre_period. Activity group: D14 merge. Tenure and follow bands: D46 seed.
with exposed_users as (
    select distinct user_id
    from {{ ref('int_exposures') }}
),

pre_counts as (
    select user_id, count(*) as n_pre_exposures
    from {{ ref('int_exposures') }}
    where period = 'pre' and event_date between '{{ var("pre_start") }}' and '{{ var("pre_end") }}'
    group by user_id
),

terciles as (
    select user_id, n_pre_exposures, ntile(3) over (order by n_pre_exposures) as activity_tercile
    from pre_counts
),

bands as (
    select dimension, band, merged_band
    from {{ ref('segment_band_map') }}
),

users as (
    select user_id, user_active_degree, register_days_range, follow_user_num_range
    from {{ ref('stg_users') }}
)

select
    x.user_id,
    coalesce(t.n_pre_exposures, 0) as n_pre_exposures,
    coalesce(cast(t.activity_tercile as string), 'no_pre_period') as activity_tercile,
    case
        when u.user_active_degree in ('full_active', 'high_active', 'middle_active') then u.user_active_degree
        when u.user_active_degree in ('2_14_day_new', 'low_active', 'single_low_active', '30day_retention', 'day_new')
            then 'new_or_low'
        else 'unknown'
    end as active_group,
    coalesce(tb.merged_band, 'unknown') as tenure_band,
    coalesce(fb.merged_band, 'unknown') as follow_band
from exposed_users as x
left join terciles as t on x.user_id = t.user_id
left join users as u on x.user_id = u.user_id
left join bands as tb on tb.dimension = 'register_days_range' and u.register_days_range = tb.band
left join bands as fb on fb.dimension = 'follow_user_num_range' and u.follow_user_num_range = fb.band
