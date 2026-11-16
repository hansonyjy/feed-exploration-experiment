{#-
  Raw KuaiRand log table for the current target: the full table on prod, the 5% hashed user sample
  (raw.<name>_dev5, decision D12) everywhere else. Only the three log tables have sample copies.
-#}
{% macro kr_log_source(table_name) -%}
    {%- if target.name == 'prod' -%}
        {{ source('kuairand', table_name) }}
    {%- else -%}
        {{ source('kuairand', table_name ~ '_dev5') }}
    {%- endif -%}
{%- endmacro %}
