with raw_data as (
    select * from
        read_json('s3://{{ var("s3_bucket") }}/landing/exercise/*.json')
),

casted_raw_data as (
    select
        id,
        title,
        {{ convert_utc_to_melbourne('start_time') }} as start_time,
        {{ convert_utc_to_melbourne('end_time') }} as end_time,
        {{ convert_utc_to_melbourne('updated_at') }} as updated_at,
        {{ convert_utc_to_melbourne('created_at') }} as created_at,
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
    rd.start_time,
    rd.end_time,
    rd.updated_at,
    rd.created_at,
    rd.ctrl_load_date,
    rd.exercises
from casted_raw_data as rd
inner join latest_dates as ld
    on
        rd.id = ld.id
        and rd.ctrl_load_date = ld.latest_ctrl_load_date
        and rd.updated_at = ld.latest_updated_at
