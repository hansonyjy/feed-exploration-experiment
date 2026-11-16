-- scope: dev5
-- HC 3: treatment-window users found in the pre-period; random-log users who also have standard
-- treatment exposures. User ids only.
with pre_users as (
    select distinct user_id from {pre} where event_date between '2022-04-08' and '2022-04-21'
),

treat_standard_users as (
    select distinct user_id from {treat} where event_date between '2022-04-22' and '2022-05-08'
),

random_users as (
    select distinct user_id from {rnd} where event_date between '2022-04-22' and '2022-05-08'
),

treatment_users as (
    select user_id from treat_standard_users
    union distinct
    select user_id from random_users
)

select
    (select count(*) from treatment_users) as n_treatment_users,
    (select count(*) from treatment_users where user_id in (select user_id from pre_users)) as n_treatment_users_in_pre,
    (select count(*) from random_users) as n_random_users,
    (select count(*) from random_users where user_id in (select user_id from treat_standard_users)) as n_random_users_with_standard
