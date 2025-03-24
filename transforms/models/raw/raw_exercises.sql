with unnested_data as (
select 
    stg_exercises.*,
    unnest(stg_exercises.sets).type as set_type,
    unnest(stg_exercises.sets).weight_kg as weight_kg,
    unnest(stg_exercises.sets).reps as reps,
    unnest(stg_exercises.sets).rpe as rpe
    from {{ ref('stg_exercises') }} stg_exercises
)
    select
        id,
        title as workout_name,
        cast(start_time as datetime) as start_time,
        cast(end_time as datetime) as end_time,
        cast(updated_at as datetime) as updated_at,
        cast(created_at as datetime) as created_at,
        index,
        title_1 as exercise_name,
        notes,
        set_type,
        weight_kg,
        reps,
        rpe,
        ctrl_load_date
    from unnested_data
