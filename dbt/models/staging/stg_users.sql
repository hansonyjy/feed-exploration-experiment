-- One row per user. -124 is KuaiRand's missing-value code and becomes null.
-- The 18 encrypted onehot_feat columns stay in raw; nothing in the design uses them.
with source as (
    select
        user_id,
        user_active_degree,
        is_lowactive_period,
        is_live_streamer,
        is_video_author,
        follow_user_num,
        follow_user_num_range,
        fans_user_num,
        fans_user_num_range,
        friend_user_num,
        friend_user_num_range,
        register_days,
        register_days_range
    from {{ source('kuairand', 'user_features') }}
)

select
    user_id,
    nullif(user_active_degree, 'UNKNOWN') as user_active_degree,
    nullif(is_lowactive_period, -124) as is_lowactive_period,
    nullif(is_live_streamer, -124) as is_live_streamer,
    nullif(is_video_author, -124) as is_video_author,
    nullif(follow_user_num, -124) as follow_user_num,
    follow_user_num_range,
    nullif(fans_user_num, -124) as fans_user_num,
    fans_user_num_range,
    nullif(friend_user_num, -124) as friend_user_num,
    friend_user_num_range,
    nullif(register_days, -124) as register_days,
    register_days_range
from source
