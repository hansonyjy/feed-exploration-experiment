-- Comparison C (D44, D57): sums and counts per user-day and item group, so the analysis can compute
-- rec(all), rec(pool) and rand rates on the same user-days, weight days by the user's random items, and
-- recombine cells for the sensitivity runs. rec(all) = rec_pool + rec_nonpool. Duration-based metrics
-- count only rows where they are defined (D51).
with items as (
    select
        *,
        case
            when is_rand = 1 then 'rand'
            when is_pool_video then 'rec_pool'
            else 'rec_nonpool'
        end as item_group
    from {{ ref('fct_tab1_impression_metrics') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['user_id', 'event_date', 'item_group', 'has_valid_duration',
                                         'is_ad_pool_video', 'is_top_user_day']) }} as cell_key,
    user_id,
    event_date,
    regime,
    item_group,
    has_valid_duration,
    is_ad_pool_video,
    is_top_user_day,
    count(*) as n_items,
    {%- for m in item_metrics() %}
    sum({{ m }}) as sum_{{ m }},
    count({{ m }}) as n_{{ m }}{{ ',' if not loop.last }}
    {%- endfor %}
from items
group by user_id, event_date, regime, item_group, has_valid_duration, is_ad_pool_video, is_top_user_day
