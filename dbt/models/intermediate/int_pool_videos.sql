-- The random policy's candidate pool: every video in the full random log (7,583 per the paper and
-- HC 2). Read from the full raw table on every target because the pool is a property of the policy,
-- not of the user sample (about 20 MB). AD-marked pool videos are flagged for the D24 sensitivity run.
with pool as (
    select distinct video_id
    from {{ source('kuairand', 'log_random_treat') }}
    where event_date between '{{ var("treat_start") }}' and '{{ var("treat_end") }}'
)

select
    p.video_id,
    v.video_type,
    coalesce(v.video_type = 'AD', false) as is_ad
from pool as p
left join {{ ref('stg_videos') }} as v on p.video_id = v.video_id
