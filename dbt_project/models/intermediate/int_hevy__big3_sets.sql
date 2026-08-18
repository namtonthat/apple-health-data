{{ config(materialized='view') }}

-- Shared Big 3 (Squat/Bench/Deadlift) working-set filter, previously duplicated
-- identically in fct_big3_prs and fct_e1rm_rolling_total.

select
    workout_date,
    exercise_name,
    weight_kg,
    reps,
    est_1rm
from {{ ref('fct_workout_sets') }}
where
    exercise_name in (
        '{{ var("squat_exercise_name") }}',
        '{{ var("bench_exercise_name") }}',
        '{{ var("deadlift_exercise_name") }}'
    )
    and set_type = 'normal'
    and est_1rm is not null
