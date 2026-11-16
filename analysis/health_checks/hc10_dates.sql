-- scope: dev5
-- HC 10: event_date range per table and agreement of event_date / hourmin with time_ms.
with exposures as (
    select 'pre' as source, event_date, hourmin, time_ms
    from {pre} where event_date between '2022-04-08' and '2022-04-21'
    union all
    select 'treat', event_date, hourmin, time_ms
    from {treat} where event_date between '2022-04-22' and '2022-05-08'
    union all
    select 'rnd', event_date, hourmin, time_ms
    from {rnd} where event_date between '2022-04-22' and '2022-05-08'
)

select
    source,
    count(*) as n_rows,
    min(event_date) as min_event_date,
    max(event_date) as max_event_date,
    countif(event_date = date(timestamp_millis(time_ms), 'Asia/Shanghai')) as n_date_match_shanghai,
    countif(event_date = date(timestamp_millis(time_ms))) as n_date_match_utc,
    countif(div(hourmin, 100) = extract(hour from timestamp_millis(time_ms) at time zone 'Asia/Shanghai')) as n_hour_match_shanghai,
    countif(mod(hourmin, 100) != 0) as n_hourmin_with_minutes
from exposures
group by source
order by source
