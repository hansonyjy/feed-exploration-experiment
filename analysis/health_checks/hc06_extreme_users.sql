-- scope: dev5
-- HC 6 (re-specified, D20): flag the top 0.1% of user-days by exposure count across all logs. Flagged
-- user-days stay in the main analysis and are excluded in a sensitivity run. Exposure counts only.
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
)

select
    t.p50 as user_day_p50,
    t.p99 as user_day_p99,
    t.p999 as user_day_p999,
    t.max_n as user_day_max,
    count(*) as n_user_days,
    countif(d.n > t.p999) as n_flagged_user_days,
    count(distinct d.user_id) as n_users,
    count(distinct if(d.n > t.p999, d.user_id, null)) as n_users_with_flagged_day,
    sum(d.n) as n_exposures,
    sum(if(d.n > t.p999, d.n, 0)) as n_flagged_exposures
from user_days as d
cross join thresholds as t
group by t.p50, t.p99, t.p999, t.max_n
