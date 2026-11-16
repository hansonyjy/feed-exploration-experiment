-- scope: dev5
-- HC 5: duplicates on the raw tables, before staging dedupes (D13).
--   exact duplicates = n_rows - n_distinct_rows (rows identical in every source column)
--   key conflicts    = (user_id, video_id, time_ms) keys carried by more than one distinct row
with all_rows as (
    select 'pre' as source, user_id, video_id, date, hourmin, time_ms, is_click, is_like, is_follow,
        is_comment, is_forward, is_hate, long_view, play_time_ms, duration_ms, profile_stay_time,
        comment_stay_time, is_profile_enter, is_rand, tab
    from {pre} where event_date between '2022-04-08' and '2022-04-21'
    union all
    select 'treat', user_id, video_id, date, hourmin, time_ms, is_click, is_like, is_follow,
        is_comment, is_forward, is_hate, long_view, play_time_ms, duration_ms, profile_stay_time,
        comment_stay_time, is_profile_enter, is_rand, tab
    from {treat} where event_date between '2022-04-22' and '2022-05-08'
    union all
    select 'rnd', user_id, video_id, date, hourmin, time_ms, is_click, is_like, is_follow,
        is_comment, is_forward, is_hate, long_view, play_time_ms, duration_ms, profile_stay_time,
        comment_stay_time, is_profile_enter, is_rand, tab
    from {rnd} where event_date between '2022-04-22' and '2022-05-08'
),

distinct_rows as (
    select distinct source, user_id, video_id, date, hourmin, time_ms, is_click, is_like, is_follow,
        is_comment, is_forward, is_hate, long_view, play_time_ms, duration_ms, profile_stay_time,
        comment_stay_time, is_profile_enter, is_rand, tab
    from all_rows
),

key_counts as (
    select source, user_id, video_id, time_ms, count(*) as n
    from distinct_rows
    group by source, user_id, video_id, time_ms
),

row_counts as (
    select source, count(*) as n_rows from all_rows group by source
),

distinct_counts as (
    select source, count(*) as n_distinct_rows from distinct_rows group by source
),

conflicts as (
    select
        source,
        countif(n > 1) as n_conflicting_keys,
        sum(if(n > 1, n, 0)) as n_rows_in_conflicting_keys
    from key_counts
    group by source
)

select
    r.source,
    r.n_rows,
    d.n_distinct_rows,
    r.n_rows - d.n_distinct_rows as n_exact_duplicate_rows,
    c.n_conflicting_keys,
    c.n_rows_in_conflicting_keys
from row_counts as r
inner join distinct_counts as d on r.source = d.source
inner join conflicts as c on r.source = c.source
order by r.source
