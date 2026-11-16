-- scope: dev5
-- HC 11: logged users and videos found in the feature tables and the category file; and whether the
-- category file's first-level id appears among the 27K tag ids (evidence final_video_id = video_id).
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
        v.tag,
        cast(c.first_level_category_id as int64) as l1_id
    from treat_videos as t
    left join {raw}.video_categories as c on t.video_id = c.final_video_id
    left join {raw}.video_features_basic as v on t.video_id = v.video_id
)

select
    (select count(*) from log_users) as n_log_users,
    (select count(*) from log_users where user_id in (select user_id from {raw}.user_features)) as n_log_users_with_features,
    (select count(*) from log_videos) as n_log_videos,
    (select count(*) from log_videos where video_id in (select video_id from {raw}.video_features_basic)) as n_log_videos_with_features,
    (select count(*) from treat_video_match) as n_treat_videos,
    (select countif(has_category) from treat_video_match) as n_treat_videos_with_category,
    (select countif(has_category and l1_id is not null and l1_id != -124 and tag is not null) from treat_video_match) as n_tag_comparable,
    (select countif(has_category and l1_id is not null and l1_id != -124 and tag is not null
        and cast(l1_id as string) in unnest(split(tag, ','))) from treat_video_match) as n_l1_in_tag
