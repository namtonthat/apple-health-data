with macros as (
    select *
    from {{ ref('raw_latest_api_metrics') }}
    where metric_name in (
        'carbohydrates',
        'fiber',
        'protein',
        'total_fat'
    )
)

select
    metric_date,
    metric_name,
    units,
    quantity
from macros
order by metric_date desc, metric_name asc
