-- scope: full
-- HC 1: random share = random / (random + standard) exposures in the treatment window, by day, tab
-- and user segment. Exposure counts only: no outcome column is read.
with exposures as (
    select event_date, tab, user_id, 0 as is_random
    from {treat}
    where event_date between '2022-04-22' and '2022-05-08'
    union all
    select event_date, tab, user_id, 1 as is_random
    from {rnd}
    where event_date between '2022-04-22' and '2022-05-08'
),

pre_activity as (
    select
        user_id,
        ntile(3) over (order by count(*)) as activity_tercile  -- exposures over the 14 pre-period days
    from {pre}
    where event_date between '2022-04-08' and '2022-04-21'
    group by user_id
),

users as (
    select
        user_id,
        case
            when user_active_degree in ('full_active', 'high_active', 'middle_active') then user_active_degree
            when user_active_degree in ('2_14_day_new', 'low_active', 'single_low_active', '30day_retention', 'day_new')
                then 'new_or_low'
            else 'unknown'
        end as active_group,  -- D14 merge rule
        coalesce(register_days_range, 'unknown') as tenure_band
    from {raw}.user_features
),

labeled as (
    select
        e.event_date,
        e.tab,
        e.is_random,
        coalesce(cast(p.activity_tercile as string), 'no_pre_period') as activity_tercile,
        coalesce(u.active_group, 'unknown') as active_group,
        coalesce(u.tenure_band, 'unknown') as tenure_band
    from exposures as e
    left join pre_activity as p on e.user_id = p.user_id
    left join users as u on e.user_id = u.user_id
)

select
    case
        when grouping(event_date) = 0 then 'day'
        when grouping(tab) = 0 then 'tab'
        when grouping(activity_tercile) = 0 then 'activity_tercile'
        when grouping(active_group) = 0 then 'active_group'
        when grouping(tenure_band) = 0 then 'tenure_band'
        else 'overall'
    end as dimension,
    coalesce(cast(event_date as string), cast(tab as string), activity_tercile, active_group, tenure_band, 'all') as cell,
    count(*) as n_exposures,
    sum(is_random) as n_random
from labeled
group by grouping sets ((), (event_date), (tab), (activity_tercile), (active_group), (tenure_band))
order by dimension, cell
