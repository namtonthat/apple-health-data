select
    load_time,
    metric_date,
    metric_name,
    quantity,
    units
from (
    select
        m.*,
        row_number() over (
            partition by m.metric_name, m.metric_date
            order by m.load_time desc
        ) as rn
    from {{ ref("raw_api_metrics") }} as m
) as t
where rn = 1
