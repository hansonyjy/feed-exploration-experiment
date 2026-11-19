{{ config(cluster_by=['user_id']) }}

-- D34: (user, first-level category) pairs with a pre-period effective view on any tab. Effective view
-- uses the D25/D26/D29 rule: play_time_ms >= the bucket's reference median, valid duration only.
-- A category absent here is new to the user. Categories come from the supplementary file (D20).
with pre_rows as (
    select e.user_id, e.video_id, e.play_time_ms, b.duration_bucket
    from {{ ref('int_exposures') }} as e
    inner join {{ ref('int_duration_buckets') }} as b
        on {{ duration_bucket_join('e.duration_filled_ms', 'b') }}
    where e.period = 'pre'
        and e.event_date between '{{ var("pre_start") }}' and '{{ var("pre_end") }}'
        and e.has_valid_duration
),

effective_views as (
    select p.user_id, p.video_id
    from pre_rows as p
    inner join {{ ref('int_reference_thresholds') }} as r on p.duration_bucket = r.duration_bucket
    where p.play_time_ms >= r.median_play_time_ms
)

select distinct
    {{ dbt_utils.generate_surrogate_key(['v.user_id', 'c.category_l1_id']) }} as user_category_key,
    v.user_id,
    c.category_l1_id
from effective_views as v
inner join {{ ref('stg_video_categories') }} as c on v.video_id = c.final_video_id
where c.category_l1_id is not null
