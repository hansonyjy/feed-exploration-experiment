{{ config(cluster_by=['user_id']) }}

-- One row per feed request (distinct user_id, time_ms) across both logs and all tabs, 2022-04-08 to
-- 05-08 (D35). A new session starts after a gap of 30 minutes or more. Session exit (D36): the session
-- ends within this request or the next 2 requests, counting requests across all tabs (D50).
-- Right-censoring (D38): requests in the last 30 minutes of 2022-05-08, Asia/Shanghai, are flagged.
with requests as (
    select user_id, time_ms, any_value(request_key) as request_key, min(event_date) as event_date
    from {{ ref('int_exposures') }}
    group by user_id, time_ms
),

gaps as (
    select
        request_key,
        user_id,
        time_ms,
        event_date,
        if(
            lag(time_ms) over (partition by user_id order by time_ms) is null
            or time_ms - lag(time_ms) over (partition by user_id order by time_ms) >= 30 * 60 * 1000,
            1, 0
        ) as is_session_start
    from requests
),

numbered as (
    select
        request_key,
        user_id,
        time_ms,
        event_date,
        sum(is_session_start) over (partition by user_id order by time_ms) as session_number
    from gaps
),

positioned as (
    select
        request_key,
        user_id,
        time_ms,
        event_date,
        session_number,
        row_number() over (partition by user_id, session_number order by time_ms) as request_seq,
        count(*) over (partition by user_id, session_number) as n_requests_in_session
    from numbered
)

select
    request_key,
    user_id,
    time_ms,
    event_date,
    session_number,
    request_seq,
    n_requests_in_session,
    n_requests_in_session - request_seq as n_requests_after,
    n_requests_in_session - request_seq <= 2 as is_session_exit_within_3,
    time_ms >= unix_millis(timestamp('2022-05-09 00:00:00', 'Asia/Shanghai')) - 30 * 60 * 1000 as is_censored
from positioned
