{{ config(
    materialized='incremental',
    unique_key='metric_date',
    partition_by={'field': 'metric_date', 'data_type': 'date'},
    on_schema_change='sync_all_columns'
) }}

with sleep_metrics as (
    select
        metric_date,
        sum(case when metric_name = 'asleep' then quantity else 0 end)
            as asleep,
        sum(case when metric_name = 'in_bed' then quantity else 0 end)
            as in_bed,
        sum(case when metric_name = 'deep_sleep' then quantity else 0 end)
            as deep_sleep
    from {{ ref('semantic_health') }}
    where metric_date >= current_date - interval '1 year'
    group by metric_date
),

bedtime as (
    select
        metric_date,
        max(case when metric_name = 'sleep_start' then sleep_times end)
            as sleep_start,
        strftime(
            max(case when metric_name = 'sleep_start' then sleep_times end),
            '%I'
        ) as sleep_start_hour,
        strftime(
            max(case when metric_name = 'sleep_start' then sleep_times end),
            '%M'
        ) as sleep_start_min,
        strftime(
            max(case when metric_name = 'sleep_start' then sleep_times end),
            '%p'
        ) as sleep_start_period
    from {{ ref('semantic_sleep_times') }}
    where metric_date >= current_date - interval '1 year'
    group by metric_date
),

aggregated as (
    select
        m.metric_date,
        round(m.asleep, 1) as asleep,
        round(m.in_bed, 1) as in_bed,
        round(m.deep_sleep, 1) as deep_sleep,
        coalesce(round((m.asleep / nullif(m.in_bed, 0) * 100), 0), 0)
            as efficiency,
        b.sleep_start,
        b.sleep_start_hour,
        b.sleep_start_min,
        b.sleep_start_period
    from sleep_metrics as m
    left join bedtime as b
        on m.metric_date = b.metric_date
)

select
    metric_date,
    'asleep' as metric_name,
    asleep as quantity,
    'hr' as units
from aggregated

union all

select
    metric_date,
    'in_bed' as metric_name,
    in_bed as quantity,
    'hr' as units
from aggregated

union all

select
    metric_date,
    'deep_sleep' as metric_name,
    deep_sleep as quantity,
    'hr' as units
from aggregated

union all

select
    metric_date,
    'efficiency' as metric_name,
    efficiency as quantity,
    '%' as units
from aggregated

union all

select
    metric_date,
    'in_bed_time' as metric_name,
    round(
        cast(sleep_start_hour as double)
        + cast(sleep_start_min as double) * 0.01,
        2
    ) as quantity,
    sleep_start_period as units
from aggregated

{% if is_incremental() %}
    where
        metric_date > (select max(metric_date) from {{ this }}) - interval 14
    days
{% endif %}

order by metric_date desc, metric_name asc
