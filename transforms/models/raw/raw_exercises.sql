with unnested_data as (
    select
        se.*,
        unnest(se.exercises, recursive := true) -- noqa: AL03
    from {{ ref('stg_exercises') }} as se
),

unnested_exercise_data as (
    select
        ud.*,
        unnest(ud.sets).type as set_type,
        unnest(ud.sets).weight_kg as weight_kg,
        unnest(ud.sets).reps as reps,
        unnest(ud.sets).rpe as rpe
    from unnested_data as ud
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
from unnested_exercise_data
