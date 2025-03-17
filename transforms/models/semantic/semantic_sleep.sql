-- Data related to the user's time in bed

with in_bed as (
    select
        rs.metric_date,
        'in_bed' as metric_name,
        rs.units,
        data_fields.inbed as quantity
    from {{ ref('raw_sleep') }} as rs
),

asleep as (
    select
        rs.metric_date,
        'asleep' as metric_name,
        rs.units,
        data_fields.asleep as quantity
    from {{ ref('raw_sleep') }} as rs
),

deep as (
    select
        rs.metric_date,
        'deep_sleep' as metric_name,
        rs.units,
        data_fields.deep as quantity
    from {{ ref('raw_sleep') }} as rs
),

all_sleep_data as (
    select * from in_bed
    union all
    select * from asleep
    union all
    select * from deep
)

select
    asd.metric_date,
    asd.metric_name,
    asd.units,
    round(asd.quantity, 1) as quantity
from all_sleep_data as asd

order by asd.metric_date asc, asd.metric_name asc
