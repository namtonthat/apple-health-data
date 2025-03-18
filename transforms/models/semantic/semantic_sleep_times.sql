with sleep_start as (
    select
        rs.metric_date,
        'sleep_start' as metric_name,
        data_fields.sleepstart as quantity
    from {{ ref('raw_sleep') }} as rs
),

sleep_end as (
    select
        rs.metric_date,
        'sleep_end' as metric_name,
        data_fields.sleepend as quantity
    from {{ ref('raw_sleep') }} as rs
),

all_sleep_data as (
    select * from sleep_start
    union
    select * from sleep_end
)

select
    asd.metric_date,
    asd.metric_name,
    strptime(asd.quantity, '%Y-%m-%d %H:%M:%S %z') as sleep_times,
    'timestamp with timezone' as units
from all_sleep_data as asd
order by asd.metric_date asc, asd.metric_name asc
