with raw_api_metrics as (
    select
        load_time,
        cast(unnest(data_fields).date as date) as metric_date,
        metric_name,
        units,
        round(unnest(data_fields).qty, 2) as quantity
    from {{ ref('stg_api_metrics') }}
)

select *
from raw_api_metrics
order by load_time desc, metric_date asc, metric_name asc
