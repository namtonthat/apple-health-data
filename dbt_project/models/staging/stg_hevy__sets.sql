{{ config(materialized='view') }}

-- Source: Hevy sets data from dlt landing zone (Delta table)
-- Path: s3://{bucket}/landing/hevy/workouts__exercises__sets/

with source as (
    select * from delta_scan('s3://{{ var("s3_bucket") }}/landing/hevy/workouts__exercises__sets')
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
        rpe,

        -- Cardio/endurance metrics
        distance_meters,
        duration_seconds,

        -- Other
        custom_metric,

        -- dlt metadata
        _dlt_list_idx as list_index

    from source
)

select * from staged
