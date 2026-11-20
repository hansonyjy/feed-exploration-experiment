{{ config(cluster_by=['user_id']) }}

-- Items of every tab-1 request that contains a random item: the input to the primary Comparison A
-- (within request, D18) and its request fixed-effects regressions (D49). Only these requests carry
-- within-request variation in is_rand.
select
    exposure_key,
    request_key,
    user_id,
    event_date,
    regime,
    is_rand,
    has_valid_duration,
    duration_bucket,
    is_ad_pool_video,
    is_top_user_day,
    {{ item_metrics() | join(',\n    ') }}
from {{ ref('fct_tab1_impression_metrics') }}
where request_has_random
