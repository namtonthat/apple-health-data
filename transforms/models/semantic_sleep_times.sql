with sleep_start as (
    select
        cast(unnest(data_fields).date as date) as metric_date,
        'sleep_start' as metric_name,
        unnest(data_fields).sleepstart as quantity
    from {{ ref('raw_sleep') }}
),

sleep_end as (
    select
        cast(unnest(data_fields).date as date) as metric_date,
        'sleep_end' as metric_name,
        unnest(data_fields).sleepend as quantity
    from {{ ref('raw_sleep') }}
),

all_sleep_data as (
    select * from sleep_start
    union
    select * from sleep_end
)

select
    metric_date,
    metric_name,
    'timestamp with timezone' as units,
    strptime(quantity, '%Y-%m-%d %H:%M:%S %z') as sleep_times
from all_sleep_data
order by metric_date asc, metric_name asc
