with raw_data as (
    select * from
        read_json('s3://{{ var("s3_bucket") }}/landing/exercise/*.json')
),

casted_raw_data as (
    select
        id,
        title,
        cast(start_time as datetime) as start_time,
        cast(end_time as datetime) as end_time,
        cast(updated_at as datetime) as updated_at,
        cast(created_at as datetime) as created_at,
        cast(ctrl_load_date as datetime) as ctrl_load_date,
        exercises
    from raw_data
),

latest_dates as (
    select
        id,
        max(updated_at) as latest_updated_at,
        max(ctrl_load_date) as latest_ctrl_load_date
    from casted_raw_data
    group by id
)

select
    rd.id,
    rd.title,
    timezone('Australia/Melbourne', rd.start_time) as start_time,
    timezone('Australia/Melbourne', rd.end_time) as end_time,
    timezone('Australia/Melbourne', rd.updated_at) as updated_at,
    timezone('Australia/Melbourne', rd.created_at) as created_at,
    rd.ctrl_load_date,
    rd.exercises
from casted_raw_data as rd
inner join latest_dates as ld
    on
        rd.id = ld.id
        and rd.ctrl_load_date = ld.latest_ctrl_load_date
        and rd.updated_at = ld.latest_updated_at
