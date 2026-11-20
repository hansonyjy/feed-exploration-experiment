-- Session exit for Comparison A (D37): requests with a random item vs requests without, within user and
-- day. One row per user-day and request type, split by the flags the main run and sensitivity runs
-- filter on (D51). Censored requests (D38) are excluded.
with requests as (
    select
        request_key,
        any_value(user_id) as user_id,
        any_value(event_date) as event_date,
        any_value(regime) as regime,
        logical_or(request_has_random) as has_random,
        coalesce(logical_or(is_rand = 1 and has_valid_duration), false) as random_item_valid,
        coalesce(logical_or(is_rand = 1 and is_ad_pool_video), false) as random_item_ad,
        any_value(is_top_user_day) as is_top_user_day,
        any_value(session_exit_request) as session_exit
    from {{ ref('fct_tab1_impression_metrics') }}
    where not is_censored
    group by request_key
)

select
    {{ dbt_utils.generate_surrogate_key(['user_id', 'event_date', 'has_random', 'random_item_valid',
                                         'random_item_ad', 'is_top_user_day']) }} as cell_key,
    user_id,
    event_date,
    regime,
    has_random,
    random_item_valid,
    random_item_ad,
    is_top_user_day,
    count(*) as n_requests,
    sum(session_exit) as n_session_exit
from requests
group by user_id, event_date, regime, has_random, random_item_valid, random_item_ad, is_top_user_day
