-- scope: full
-- HC 9: is_rand values in the standard logs, and whether random exposures also appear in the standard
-- treatment log. Keys and flags only, no outcomes.
with random_rows as (
    select distinct user_id, video_id, time_ms
    from {rnd}
    where event_date between '2022-04-22' and '2022-05-08'
),

standard_keys as (
    select distinct user_id, video_id, time_ms
    from {treat}
    where event_date between '2022-04-22' and '2022-05-08'
),

standard_user_times as (
    select distinct user_id, time_ms
    from {treat}
    where event_date between '2022-04-22' and '2022-05-08'
),

is_rand_values as (
    select 'pre' as source, countif(is_rand != 0 or is_rand is null) as n_is_rand_not_0, count(*) as n_rows
    from {pre} where event_date between '2022-04-08' and '2022-04-21'
    union all
    select 'treat', countif(is_rand != 0 or is_rand is null), count(*)
    from {treat} where event_date between '2022-04-22' and '2022-05-08'
)

select
    (select sum(n_is_rand_not_0) from is_rand_values where source = 'pre') as pre_n_is_rand_not_0,
    (select sum(n_rows) from is_rand_values where source = 'pre') as pre_n_rows,
    (select sum(n_is_rand_not_0) from is_rand_values where source = 'treat') as treat_n_is_rand_not_0,
    (select sum(n_rows) from is_rand_values where source = 'treat') as treat_n_rows,
    (select count(*) from random_rows) as n_random_keys,
    (select count(*) from random_rows as r
        inner join standard_keys as s
            on r.user_id = s.user_id and r.video_id = s.video_id and r.time_ms = s.time_ms) as n_random_keys_in_standard,
    (select count(*) from random_rows as r
        inner join standard_user_times as s
            on r.user_id = s.user_id and r.time_ms = s.time_ms) as n_random_user_time_in_standard
