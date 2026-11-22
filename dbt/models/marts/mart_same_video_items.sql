{{ config(cluster_by=['video_id']) }}

-- Comparison B (D43): every tab-1 exposure of a pool video (the 7,583 candidates), 2022-04-23 to 05-08,
-- in either arm. Item rows, so the analysis can weight each video equally, bootstrap by video or by
-- user, and run the video fixed-effects regression. Videos without an exposure in each arm are dropped
-- in the analysis, not here.
select
    exposure_key,
    video_id,
    user_id,
    event_date,
    regime,
    is_rand,
    has_valid_duration,
    is_ad_pool_video,
    is_top_user_day,
    {{ item_metrics() | join(',\n    ') }}
from {{ ref('fct_tab1_impression_metrics') }}
where is_pool_video
