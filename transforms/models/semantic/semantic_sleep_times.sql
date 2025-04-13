{{ config(
    materialized='incremental',
    unique_key='metric_date || metric_name',
    partition_by={'field': 'metric_date', 'data_type': 'date'}
) }}

with all_sleep_data as (
    select
        rs.metric_date,
        'sleep_start' as metric_name,
        rs.data_fields.sleepstart as quantity
    from {{ ref('raw_sleep') }} as rs
    where rs.data_fields.sleepstart is not null

    union all

    select
        rs.metric_date,
        'sleep_end' as metric_name,
        rs.data_fields.sleepend as quantity
    from {{ ref('raw_sleep') }} as rs
    where rs.data_fields.sleepend is not null
)

select
    asd.metric_date,
    asd.metric_name,
    strptime(asd.quantity, '%Y-%m-%d %H:%M:%S %z') as sleep_times,
    'timestamp with timezone' as units
from all_sleep_data as asd

{% if is_incremental() %}
    where asd.metric_date > (select max(metric_date) from {{ this }}) - interval '14 days'
{% endif %}

order by asd.metric_date asc, asd.metric_name asc
