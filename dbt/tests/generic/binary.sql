{#- Fails on any non-null value other than 0 or 1. -#}
{% test binary(model, column_name) %}
    select {{ column_name }}
    from {{ model }}
    where {{ column_name }} not in (0, 1)
{% endtest %}
