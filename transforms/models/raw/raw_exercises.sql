select
    id,
    title as workout_name,
    cast(start_time as date),
    cast(end_time as date),
    cast(updated_at as date),
    cast(created_at as date),
    index,
    title_1 as exercise_name,
    notes,
    set_type,
    weight_kg,
    reps,
    rpe
from {{ ref('stg_exercises') }}
