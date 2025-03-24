select
    id,
    title as workout_name,
    start_time,
    end_time,
    index,
    title_1 as exercise_name,
    notes,
    set_type,
    weight_kg,
    reps,
    rpe
from {{ ref('raw_exercises') }}
