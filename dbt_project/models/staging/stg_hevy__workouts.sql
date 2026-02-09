{{ config(materialized='view') }}

-- Source: Cleansed Hevy workout data from raw zone
-- Path: s3://{bucket}/raw/hevy/workouts/*.parquet

with source as (
    select * from read_parquet('s3://{{ var("s3_bucket") }}/raw/hevy/workouts/*.parquet', union_by_name=true)
),

staged as (
    select
        -- Primary key (handle both old and new column names)
        coalesce(_dlt_id, dlt_id) as workout_id,

        -- Natural key
        id as hevy_workout_id,

        -- Timestamps
        start_time::timestamp as started_at,
        end_time::timestamp as ended_at,
        created_at::timestamp as created_at,
        updated_at::timestamp as updated_at,

        -- Derived date/time fields
        start_time::date as workout_date,
        dayname(start_time::timestamp) as day_name,
        extract('hour' from start_time::timestamp)::int as start_hour,
        extract('minute' from end_time::timestamp - start_time::timestamp) as duration_minutes,

        -- Workout details
        coalesce(title, 'Untitled Workout') as workout_name,
        description,

        -- dlt metadata
        _dlt_load_id as load_id,

        -- Deduplicate: dlt appends full dumps each extraction,
        -- keep one record per Hevy workout (most recently updated)
        row_number() over (
            partition by id
            order by updated_at desc, _dlt_load_id desc
        ) as row_num

    from source
)

select * from staged
where row_num = 1
