select
    id,
    workout_name,
    cast(start_time as date) as metric_date,
    start_time,
    round(extract(epoch from workout_duration) / 60, 0)
        as workout_duration_mins,
    index,
    exercise_name,
    notes,
    set_type,
    round(weight_kg, 1) as weight_kg,
    reps,
    rpe
from {{ ref('raw_exercises') }}
order by metric_date asc
