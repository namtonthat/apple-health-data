{{
  config(
    materialized='external',
    location='s3://{{ var("s3_bucket") }}/transformed/fct_big3_prs'
  )
}}

-- All-time best estimated 1RM for each Big 3 lift (Squat, Bench, Deadlift).
-- Grain: one row per lift. Carries the weight/reps/date of the set that produced
-- the best e1RM so the dashboard can show the lift and compare to competition PRs
-- without scanning the full set history in Python.

with big3_sets as (
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
),

ranked as (
    select
        *,
        row_number() over (
            partition by exercise_name
            order by est_1rm desc, workout_date desc
        ) as rn
    from big3_sets
)

select
    case exercise_name
        when '{{ var("squat_exercise_name") }}' then 'squat'
        when '{{ var("bench_exercise_name") }}' then 'bench'
        when '{{ var("deadlift_exercise_name") }}' then 'deadlift'
    end as lift,
    exercise_name,
    est_1rm as best_e1rm,
    weight_kg as best_weight_kg,
    reps as best_reps,
    workout_date as pr_date
from ranked
where rn = 1
order by lift
