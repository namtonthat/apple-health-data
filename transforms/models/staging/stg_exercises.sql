with raw_data as (
    select
        id,
        title,
        {{ convert_utc_to_melbourne('start_time') }} as start_time,
        {{ convert_utc_to_melbourne('end_time') }} as end_time,
        {{ convert_utc_to_melbourne('updated_at') }} as updated_at,
        {{ convert_utc_to_melbourne('created_at') }} as created_at,
        cast(ctrl_load_date as datetime) as ctrl_load_date,
        exercises
    from {{ source('s3_landing', 'hevy') }}
    {% if is_incremental() %}
        where ctrl_load_date >= current_date - interval '15' day
    {% endif %}
),

ranked as (
    select
        *,
        row_number() over (
            partition by id
            order by updated_at desc, ctrl_load_date desc
        ) as rn
    from raw_data
)

select *
from ranked
where rn = 1
