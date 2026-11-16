-- scope: dev5
-- HC 11: logged users and videos found in the feature tables and in the supplementary category file.
-- Categories come from the supplementary file only (D20); the 27K tag column is not used.
with log_users as (
    select distinct user_id from {pre} where event_date between '2022-04-08' and '2022-04-21'
    union distinct
    select distinct user_id from {treat} where event_date between '2022-04-22' and '2022-05-08'
    union distinct
    select distinct user_id from {rnd} where event_date between '2022-04-22' and '2022-05-08'
),

log_videos as (
    select distinct video_id from {pre} where event_date between '2022-04-08' and '2022-04-21'
    union distinct
    select distinct video_id from {treat} where event_date between '2022-04-22' and '2022-05-08'
    union distinct
    select distinct video_id from {rnd} where event_date between '2022-04-22' and '2022-05-08'
),

treat_videos as (
    select distinct video_id from {treat} where event_date between '2022-04-22' and '2022-05-08'
    union distinct
    select distinct video_id from {rnd} where event_date between '2022-04-22' and '2022-05-08'
),

treat_video_match as (
    select
        t.video_id,
        c.final_video_id is not null as has_category,
        c.final_video_id is not null and c.first_level_category_id != -124 as has_l1_category
    from treat_videos as t
    left join {raw}.video_categories as c on t.video_id = c.final_video_id
)

select
    (select count(*) from log_users) as n_log_users,
    (select count(*) from log_users where user_id in (select user_id from {raw}.user_features)) as n_log_users_with_features,
    (select count(*) from log_videos) as n_log_videos,
    (select count(*) from log_videos where video_id in (select video_id from {raw}.video_features_basic)) as n_log_videos_with_features,
    (select count(*) from treat_video_match) as n_treat_videos,
    (select countif(has_category) from treat_video_match) as n_treat_videos_with_category,
    (select countif(has_l1_category) from treat_video_match) as n_treat_videos_with_l1_category
