-- scope: full
-- HC 1c (post-hoc, D21): share of tab-1 feed requests that contain a random item, the paper's unit
-- ("a fixed probability" per recommended list). A request is a distinct (user_id, time_ms) in tab 1.
-- Also reports exposure-level shares and items per request. Counts only: no outcome column is read.
-- Window: 2022-04-23 to 05-08 (April 22, a partial first day, is excluded, D22).
-- Regimes: low = 04-23 to 05-01, transition = 05-02 (reported, not judged), high = 05-03 to 05-08.
with items as (
    select user_id, time_ms, event_date, 0 as is_random
    from {treat}
    where event_date between '2022-04-23' and '2022-05-08' and tab = 1
    union all
    select user_id, time_ms, event_date, 1 as is_random
    from {rnd}
    where event_date between '2022-04-23' and '2022-05-08' and tab = 1
),

requests as (
    select
        user_id,
        time_ms,
        min(event_date) as event_date,
        count(*) as n_items,
        sum(is_random) as n_random_items
    from items
    group by user_id, time_ms
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
            when r.event_date <= '2022-05-01' then 'low'
            when r.event_date = '2022-05-02' then 'transition'
            else 'high'
        end as regime,
        r.event_date,
        r.n_items,
        r.n_random_items,
        coalesce(cast(p.activity_tercile as string), 'no_pre_period') as activity_tercile,
        coalesce(u.active_group, 'unknown') as active_group,
        coalesce(u.tenure_band, 'unknown') as tenure_band
    from requests as r
    left join pre_activity as p on r.user_id = p.user_id
    left join users as u on r.user_id = u.user_id
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
    count(*) as n_requests,
    countif(n_random_items > 0) as n_random_requests,
    countif(n_random_items > 1) as n_requests_multi_random,
    sum(n_items) as n_exposures,
    sum(n_random_items) as n_random
from labeled
group by grouping sets (
    (regime), (regime, event_date), (regime, activity_tercile), (regime, active_group), (regime, tenure_band)
)
order by regime, dimension, cell
