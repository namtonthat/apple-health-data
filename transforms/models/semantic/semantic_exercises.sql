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
    round(weight_kg / 1.25) * 1.25 as weight_kg,
    reps,
    rpe,
    round((weight_kg * reps) / 1.25) * 1.25 as volume
from {{ ref('raw_exercises') }}
order by metric_date asc
