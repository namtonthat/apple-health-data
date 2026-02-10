{{ config(materialized='view') }}

-- Source: Hevy exercise data from dlt landing zone
-- Path: s3://{bucket}/landing/hevy/workouts__exercises/*.parquet

with source as (
    select * from read_parquet('s3://{{ var("s3_bucket") }}/landing/hevy/workouts__exercises/*.parquet', union_by_name = true)
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

        -- dlt metadata
        _dlt_list_idx as list_index

    from source
)

select * from staged
