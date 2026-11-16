-- scope: dev5
-- HC 6: exposures per user-day across all logs; users flagged as possible bots or test accounts.
with exposures as (
    select user_id, event_date from {pre} where event_date between '2022-04-08' and '2022-04-21'
    union all
    select user_id, event_date from {treat} where event_date between '2022-04-22' and '2022-05-08'
    union all
    select user_id, event_date from {rnd} where event_date between '2022-04-22' and '2022-05-08'
),

user_days as (
    select user_id, event_date, count(*) as n
    from exposures
    group by user_id, event_date
),

thresholds as (
    select
        approx_quantiles(n, 1000)[offset(500)] as p50,
        approx_quantiles(n, 1000)[offset(990)] as p99,
        approx_quantiles(n, 1000)[offset(999)] as p999,
        max(n) as max_n
    from user_days
),

users as (
    select user_id, max(n) as max_daily, sum(n) as total
    from user_days
    group by user_id
)

select
    t.p50 as user_day_p50,
    t.p99 as user_day_p99,
    t.p999 as user_day_p999,
    t.max_n as user_day_max,
    count(*) as n_users,
    countif(u.max_daily > 2000 or u.max_daily > t.p999) as n_flagged_users,
    sum(u.total) as n_exposures,
    sum(if(u.max_daily > 2000 or u.max_daily > t.p999, u.total, 0)) as n_flagged_exposures
from users as u
cross join thresholds as t
group by t.p50, t.p99, t.p999, t.max_n
