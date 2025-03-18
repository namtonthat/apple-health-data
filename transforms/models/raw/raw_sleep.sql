select
    cast(unnest(data_fields).date as date) as metric_date,
    units,
    unnest(data_fields) as data_fields
from (
    select * from {{ ref('stg_api_metrics') }}
    where metric_name = 'sleep_analysis'
) as m
