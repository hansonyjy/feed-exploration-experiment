{#- Fails on any value below zero (nulls pass; not_null tests cover those). -#}
{% test non_negative(model, column_name) %}
    select {{ column_name }}
    from {{ model }}
    where {{ column_name }} < 0
{% endtest %}
