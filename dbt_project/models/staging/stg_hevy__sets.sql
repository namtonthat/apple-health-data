{{ config(materialized='view') }}

-- Source: Cleansed Hevy sets data from raw zone
-- Path: s3://{bucket}/raw/hevy/workouts__exercises__sets/*.parquet

with source as (
    select * from read_parquet('s3://{{ var("s3_bucket") }}/raw/hevy/workouts__exercises__sets/*.parquet')
),

staged as (
    select
        -- Primary key
        _dlt_id as set_id,

        -- Foreign key
        _dlt_parent_id as exercise_id,

        -- Set details
        index + 1 as set_number,  -- 1-indexed for readability
        type as set_type,

        -- Performance metrics (handle variant types from dlt)
        coalesce(weight_kg__v_double, weight_kg::double) as weight_kg,
        reps,
        coalesce(rpe__v_double, rpe::double) as rpe,

        -- Cardio/endurance metrics
        distance_meters,
        duration_seconds,

        -- Other
        custom_metric,

        -- Cleanse metadata
        _load_timestamp,
        _source_file,
        _source_system

    from source
)

select * from staged
