-- scope: full
-- HC 1b (post-hoc re-specification, D16): random share within tab 1, by date regime, and by day and
-- user segment within each regime. Exposure counts only: no outcome column is read.
-- Regimes (D17), set from the HC 1 daily random shares: low = 2022-04-22 to 05-01,
-- transition = 2022-05-02 (switch happens within the day; reported, not judged), high = 05-03 to 05-08.
with exposures as (
    select event_date, user_id, 0 as is_random
    from {treat}
    where event_date between '2022-04-22' and '2022-05-08' and tab = 1
    union all
    select event_date, user_id, 1 as is_random
    from {rnd}
    where event_date between '2022-04-22' and '2022-05-08' and tab = 1
),

pre_activity as (
    select
        user_id,
        ntile(3) over (order by count(*)) as activity_tercile
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
        end as active_group,
        coalesce(register_days_range, 'unknown') as tenure_band
    from {raw}.user_features
),

labeled as (
    select
        case
            when e.event_date <= '2022-05-01' then 'low'
            when e.event_date = '2022-05-02' then 'transition'
            else 'high'
        end as regime,
        e.event_date,
        e.is_random,
        coalesce(cast(p.activity_tercile as string), 'no_pre_period') as activity_tercile,
        coalesce(u.active_group, 'unknown') as active_group,
        coalesce(u.tenure_band, 'unknown') as tenure_band
    from exposures as e
    left join pre_activity as p on e.user_id = p.user_id
    left join users as u on e.user_id = u.user_id
)

select
    regime,
    case
        when grouping(event_date) = 0 then 'day'
        when grouping(activity_tercile) = 0 then 'activity_tercile'
        when grouping(active_group) = 0 then 'active_group'
        when grouping(tenure_band) = 0 then 'tenure_band'
        else 'regime'
    end as dimension,
    coalesce(cast(event_date as string), activity_tercile, active_group, tenure_band, 'all') as cell,
    count(*) as n_exposures,
    sum(is_random) as n_random
from labeled
group by grouping sets (
    (regime), (regime, event_date), (regime, activity_tercile), (regime, active_group), (regime, tenure_band)
)
order by regime, dimension, cell
