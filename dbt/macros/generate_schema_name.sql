{#-
  prod: models go to their configured dataset as named (staging, marts), with no target prefix.
  any other target (dev): every model goes to the target dataset (`dev`).
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if target.name == 'prod' and custom_schema_name is not none -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ target.schema }}
    {%- endif -%}
{%- endmacro %}
