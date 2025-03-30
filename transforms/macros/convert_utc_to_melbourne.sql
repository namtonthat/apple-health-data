{% macro convert_utc_to_melbourne(column_name) %}
    CAST({{ column_name }} AS TIMESTAMPTZ) AT TIME ZONE 'Australia/Melbourne'
{% endmacro %}
