{{ config(materialized='view') }}

-- Source: Cleansed Hevy exercise data from raw zone
-- Path: s3://{bucket}/raw/hevy/workouts__exercises/*.parquet

with source as (
    select * from read_parquet('s3://{{ var("s3_bucket") }}/raw/hevy/workouts__exercises/*.parquet')
),

staged as (
    select
        -- Primary key
        _dlt_id as exercise_id,

        -- Foreign key
        _dlt_parent_id as workout_id,

        -- Exercise details
        title as exercise_name,
        exercise_template_id,
        index as exercise_order,
        superset_id,
        notes,

        -- Cleanse metadata
        _load_timestamp,
        _source_file,
        _source_system

    from source
)

select * from staged
