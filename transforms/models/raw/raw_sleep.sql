with all_sleep_metrics as (
    select
        load_time,
        cast(unnest(data_fields).date as date) as metric_date,
        units,
        unnest(data_fields) as data_fields
    from (
        select * from {{ ref('stg_api_metrics') }}
        where metric_name = 'sleep_analysis'
    ) as m
),

sleep_ranked as (
    select
        asm.*,
        row_number() over (
            partition by asm.metric_date
            order by asm.load_time asc
        ) as rn
    from all_sleep_metrics as asm
)

select
    load_time,
    metric_date,
    data_fields,
    units
from sleep_ranked
where rn = 1
order by metric_date desc
