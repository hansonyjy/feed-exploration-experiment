-- Item-level segments of each random item (D47), one row per tab-1 request with a random item
-- (2022-04-23 to 05-08; a request never holds two random items, HC 1c). Duration segment: the item's D26
-- bucket (null without a valid duration; such requests are outside the main run). Category segment: the
-- first-level category from the supplementary file; categories with fewer than 1,000 random exposures in
-- the window (a count, not an outcome) and videos without a category form `other`.
with random_items as (
    select request_key, user_id, video_id, duration_bucket, category_l1_id
    from {{ ref('int_tab1_impressions') }}
    where is_rand = 1
),

category_names as (
    select category_l1_id, any_value(category_l1_name) as category_l1_name
    from {{ ref('stg_video_categories') }}
    where category_l1_id is not null
    group by category_l1_id
),

category_counts as (
    select category_l1_id, count(*) as n_category_random_exposures
    from random_items
    where category_l1_id is not null
    group by category_l1_id
)

select
    r.request_key,
    r.user_id,
    r.video_id,
    r.duration_bucket,
    r.category_l1_id,
    n.category_l1_name,
    c.n_category_random_exposures,
    case
        when c.n_category_random_exposures >= 1000 then cast(r.category_l1_id as string)
        else 'other'
    end as category_segment
from random_items as r
left join category_counts as c on r.category_l1_id = c.category_l1_id
left join category_names as n on r.category_l1_id = n.category_l1_id
