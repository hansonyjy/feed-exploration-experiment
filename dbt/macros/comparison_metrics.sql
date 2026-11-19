{#- Item-level metrics compared in Comparison A, in reporting order (analysis_plan.md). Session exit is
    request-level and handled separately (D37). -#}
{% macro item_metrics() -%}
    {{ return(['effective_view', 'naive_completion', 'watch_time_ms', 'like_', 'comment_', 'forward_',
               'profile_enter', 'new_author_follow', 'new_category_effective_view', 'hate', 'fast_skip']) }}
{%- endmacro %}
