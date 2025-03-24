with volume_data as (
    select
        id,
        index,
        metric_date,
        start_time,
        exercise_name,
        workout_duration_mins,
        sum(weight_kg * reps) as volume_kg
    from {{ ref('semantic_exercises') }}
    group by all
    order by start_time desc, index asc
)

select
    metric_date,
    exercise_name,
    workout_duration_mins,
    volume_kg
from volume_data
