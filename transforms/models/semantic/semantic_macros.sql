with macros as (
    select *
    from {{ ref('raw_api_metrics') }}
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
from (
    select
        m.*,
        row_number() over (
            partition by m.metric_name, m.metric_date
            order by m.load_time desc
        ) as rn
    from macros as m
) as t
where rn = 1
order by metric_date desc, metric_name asc
