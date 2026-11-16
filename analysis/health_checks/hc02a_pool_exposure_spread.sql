-- scope: full
-- HC 2a: how evenly random exposures spread over pool videos (full random log, about 1.19M rows).
with per_video as (
    select video_id, count(*) as n
    from {rnd}
    where event_date between '2022-04-22' and '2022-05-08'
    group by video_id
)

select
    count(*) as n_pool_videos,
    sum(n) as n_random_exposures,
    avg(n) as mean_exposures,
    stddev_samp(n) as sd_exposures,
    safe_divide(stddev_samp(n), avg(n)) as cv_exposures,
    min(n) as min_exposures,
    max(n) as max_exposures,
    safe_divide(max(n), min(n)) as max_min_ratio,
    approx_quantiles(n, 100)[offset(1)] as p01_exposures,
    approx_quantiles(n, 100)[offset(99)] as p99_exposures
from per_video
