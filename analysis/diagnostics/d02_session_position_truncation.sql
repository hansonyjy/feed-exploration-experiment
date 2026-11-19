-- D52 (post-results, exploratory): session position and display truncation for the session-exit contrast.
-- Counts only, full raw data. Sessions are cut at 30-minute gaps across all tabs and both logs,
-- 2022-04-08 to 05-08 (D35). Scored: tab-1 requests 2022-04-23 to 05-08, excluding the last 30 minutes
-- of 2022-05-08 Asia/Shanghai (D38). Raw rows are de-duplicated to distinct requests and items.
with exposures as (
    select user_id, video_id, time_ms, tab, 0 as is_random
    from `feed-exploration-hy.raw.log_standard_pre`
    where event_date between '2022-04-08' and '2022-04-21'
    union all
    select user_id, video_id, time_ms, tab, 0 as is_random
    from `feed-exploration-hy.raw.log_standard_treat`
    where event_date between '2022-04-22' and '2022-05-08'
    union all
    select user_id, video_id, time_ms, tab, 1 as is_random
    from `feed-exploration-hy.raw.log_random_treat`
    where event_date between '2022-04-22' and '2022-05-08'
),

requests as (
    select
        user_id,
        time_ms,
        count(distinct if(tab = 1, video_id, null)) as n_tab1_items,
        max(if(tab = 1, is_random, 0)) as has_random_tab1
    from exposures
    group by user_id, time_ms
),

sessions as (
    select
        user_id,
        time_ms,
        n_tab1_items,
        has_random_tab1,
        sum(is_start) over (partition by user_id order by time_ms) as session_number
    from (
        select
            r.*,
            if(lag(time_ms) over (partition by user_id order by time_ms) is null
               or time_ms - lag(time_ms) over (partition by user_id order by time_ms) >= 30 * 60 * 1000, 1, 0)
                as is_start
        from requests as r
    )
),

positioned as (
    select
        n_tab1_items,
        has_random_tab1,
        time_ms,
        row_number() over (partition by user_id, session_number order by time_ms) as seq,
        count(*) over (partition by user_id, session_number) as n_in_session
    from sessions
),

scored as (
    select
        case
            when n_in_session - seq = 0 then 'd_last'
            when n_in_session - seq = 1 then 'c_second_last'
            when n_in_session - seq = 2 then 'b_third_last'
            when seq = 1 then 'a0_first'
            else 'a1_middle'
        end as position,
        least(n_tab1_items, 12) as n_items_capped,
        has_random_tab1
    from positioned
    where n_tab1_items > 0
        and time_ms >= unix_millis(timestamp('2022-04-23 00:00:00', 'Asia/Shanghai'))
        and time_ms < unix_millis(timestamp('2022-05-09 00:00:00', 'Asia/Shanghai')) - 30 * 60 * 1000
)

select
    position,
    n_items_capped,
    count(*) as n_requests,
    sum(has_random_tab1) as n_random_requests
from scored
group by position, n_items_capped
order by position, n_items_capped
