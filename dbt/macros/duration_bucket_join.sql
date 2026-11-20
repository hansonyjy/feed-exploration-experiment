{#-
  Join condition that assigns a duration to its D26 bucket: lower edge exclusive, upper edge inclusive,
  open-ended at both ends (D50). Usage: left join buckets as b on {{ duration_bucket_join('x.duration_filled_ms', 'b') }}
-#}
{% macro duration_bucket_join(duration_col, bucket_alias) -%}
    ({{ bucket_alias }}.lower_exclusive_ms is null or {{ duration_col }} > {{ bucket_alias }}.lower_exclusive_ms)
    and ({{ bucket_alias }}.upper_inclusive_ms is null or {{ duration_col }} <= {{ bucket_alias }}.upper_inclusive_ms)
{%- endmacro %}
