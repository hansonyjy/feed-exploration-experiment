-- Diagnostic for HC 1b: does the dataset's user filter (paper Sec. 3.2: users with fewer than 10
-- random exposures removed) explain the higher random share among light users? Counts only.
with random_per_user as (
    select user_id, count(*) as n_random
    from `feed-exploration-hy.raw.log_random_treat`
    where event_date between '2022-04-22' and '2022-05-08'
    group by user_id
),

pre_activity as (
    select user_id, count(*) as n_pre, ntile(3) over (order by count(*)) as activity_tercile
    from `feed-exploration-hy.raw.log_standard_pre`
    where event_date between '2022-04-08' and '2022-04-21'
    group by user_id
)

select
    coalesce(cast(p.activity_tercile as string), 'no_pre_period') as activity_tercile,
    count(*) as n_users,
    min(r.n_random) as min_random_per_user,
    approx_quantiles(r.n_random, 2)[offset(1)] as median_random_per_user,
    countif(r.n_random between 10 and 14) / count(*) as share_users_10_to_14_random,
    approx_quantiles(p.n_pre, 2)[offset(1)] as median_pre_exposures
from random_per_user as r
left join pre_activity as p on r.user_id = p.user_id
group by 1
order by 1
