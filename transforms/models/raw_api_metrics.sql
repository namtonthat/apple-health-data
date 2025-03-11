select
    cast(unnest(data_fields).date as date) as metric_date,
    metric_name,
    units,
    unnest(data_fields).qty as quantity
from {{ ref('stg_api_metrics') }};
