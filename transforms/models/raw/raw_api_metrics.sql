with raw_api_metrics as (
    select
        load_time,
        unnest(data_fields).date as metric_date,
        metric_name,
        units,
        round(unnest(data_fields).qty, 2) as quantity
    from {{ ref('stg_api_metrics') }}
),

raw_api_metrics_with_melbourne_time as (
    select
        load_time,
        -- Parse the datetime portion and add the +1100 offset manually
        strptime(substr(metric_date, 1, 19), '%Y-%m-%d %H:%M:%S')
        + interval 11 hour as metric_date,
        metric_name,
        units,
        quantity
    from raw_api_metrics
)

select
    load_time,
    cast(metric_date as date) as metric_date,
    metric_name,
    units,
    quantity
from raw_api_metrics_with_melbourne_time
order by load_time desc, metric_date asc, metric_name asc
