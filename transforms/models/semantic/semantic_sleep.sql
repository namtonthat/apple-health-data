-- Data related to the user's time in bed

with in_bed as (
    select
        cast(unnest(data_fields).date as date) as metric_date,
        'in_bed' as metric_name,
        units,
        unnest(data_fields).inbed as quantity
    from {{ ref('raw_sleep') }}
),

asleep as (
    select
        cast(unnest(data_fields).date as date) as metric_date,
        'asleep' as metric_name,
        units,
        unnest(data_fields).asleep as quantity
    from {{ ref('raw_sleep') }}
),

deep as (
    select
        cast(unnest(data_fields).date as date) as metric_date,
        'deep_sleep' as metric_name,
        units,
        unnest(data_fields).deep as quantity
    from {{ ref('raw_sleep') }}
),

all_sleep_data as (
    select * from in_bed
    union all
    select * from asleep
    union all
    select * from deep
)

select
    metric_date,
    metric_name,
    units,
    round(quantity, 1) as quantity
from all_sleep_data

order by metric_date asc, metric_name asc
