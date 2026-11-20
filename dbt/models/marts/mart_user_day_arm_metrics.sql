-- Sums and counts per user-day and arm for the within-user robustness check (D18) and its sensitivity
-- variants. Split by the flags each variant filters on, so the analysis can recombine cells without
-- reading item rows. Duration-based metrics count only rows where they are defined (D51).
select
    {{ dbt_utils.generate_surrogate_key(['user_id', 'event_date', 'is_rand', 'has_valid_duration',
                                         'is_ad_pool_video', 'is_top_user_day']) }} as cell_key,
    user_id,
    event_date,
    regime,
    is_rand,
    has_valid_duration,
    is_ad_pool_video,
    is_top_user_day,
    count(*) as n_items,
    {%- for m in item_metrics() %}
    sum({{ m }}) as sum_{{ m }},
    count({{ m }}) as n_{{ m }}{{ ',' if not loop.last }}
    {%- endfor %}
from {{ ref('fct_tab1_impression_metrics') }}
group by user_id, event_date, regime, is_rand, has_valid_duration, is_ad_pool_video, is_top_user_day
