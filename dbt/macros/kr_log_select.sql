{#-
  Shared staging select for the KuaiRand log tables (stg_log_standard, stg_log_random).
  Types and renames only, plus structural flags. No metric logic (duration buckets, effective views,
  sessions) belongs here; that lives in int_ models.
  Exact duplicate rows (all source columns identical) are collapsed with `select distinct`
  (decision D13). HC 5 counts them on raw before this runs.
-#}
{% macro kr_log_select(relation, source_table, period, start_date, end_date) -%}
    select distinct
        {{ dbt_utils.generate_surrogate_key(["'" ~ source_table ~ "'", 'user_id', 'video_id', 'time_ms']) }} as impression_id,
        '{{ source_table }}' as source_table,
        '{{ period }}' as period,
        user_id,
        video_id,
        event_date,
        hourmin as hour_min,
        div(hourmin, 100) as event_hour,
        time_ms,
        timestamp_millis(time_ms) as event_ts,
        is_click,
        is_like,
        is_follow,
        is_comment,
        is_forward,
        is_hate,
        long_view as is_long_view,
        is_profile_enter,
        play_time_ms,
        duration_ms,
        profile_stay_time,
        comment_stay_time,
        is_rand,
        tab,
        coalesce(duration_ms, 0) <= 0 as is_zero_duration,
        play_time_ms > duration_ms as is_play_over_duration
    from {{ relation }}
    where event_date between '{{ start_date }}' and '{{ end_date }}'
{%- endmacro %}
