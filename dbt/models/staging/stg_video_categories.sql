{{ config(cluster_by=['final_video_id']) }}

-- One row per video in the supplementary category file (D10). Ids are floats in the source;
-- -124 / UNKNOWN mark a missing level and become null. final_video_id is kept under its own name
-- until its match to 27K video_id is verified (Phase 0 check).
with source as (
    select
        final_video_id,
        first_level_category_id,
        first_level_category_name,
        first_level_category_prob,
        second_level_category_id,
        second_level_category_name,
        second_level_category_prob,
        third_level_category_id,
        third_level_category_name,
        third_level_category_prob,
        fourth_level_category_id,
        fourth_level_category_name,
        fourth_level_category_prob
    from {{ source('kuairand', 'video_categories') }}
)

select
    final_video_id,
    {%- for level in ['first', 'second', 'third', 'fourth'] %}
    nullif(safe_cast({{ level }}_level_category_id as int64), -124) as category_l{{ loop.index }}_id,
    nullif({{ level }}_level_category_name, 'UNKNOWN') as category_l{{ loop.index }}_name,
    if({{ level }}_level_category_id = -124, null, {{ level }}_level_category_prob) as category_l{{ loop.index }}_prob{{ ',' if not loop.last }}
    {%- endfor %}
from source
