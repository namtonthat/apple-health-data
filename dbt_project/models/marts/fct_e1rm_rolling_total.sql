{{
  config(
    materialized='external',
    location='s3://{{ var("s3_bucket") }}/transformed/fct_e1rm_rolling_total'
  )
}}

-- Rolling estimated 1RM total for Big 3 lifts (Squat, Bench, Deadlift)
-- Uses Epley formula: e1RM = weight × (1 + reps/30)
-- Tracks running max per lift, then sums for estimated total

with big3_sets as (
    select
        workout_date,
        exercise_name,
        weight_kg,
        reps,
        round(weight_kg * (1 + reps / 30.0), 1) as e1rm
    from {{ ref('fct_workout_sets') }}
    where
        exercise_name in (
            '{{ var("squat_exercise_name") }}',
            '{{ var("bench_exercise_name") }}',
            '{{ var("deadlift_exercise_name") }}'
        )
        and set_type = 'normal'
        and weight_kg > 0
        and reps > 0
),

best_per_day as (
    select
        workout_date,
        exercise_name,
        max(e1rm) as best_e1rm
    from big3_sets
    group by workout_date, exercise_name
),

running_max as (
    select
        workout_date,
        exercise_name,
        max(best_e1rm) over (
            partition by exercise_name
            order by workout_date
            rows between unbounded preceding and current row
        ) as running_max_e1rm
    from best_per_day
),

pivoted as (
    select
        workout_date,
        max(case when exercise_name = '{{ var("squat_exercise_name") }}' then running_max_e1rm end)
            as squat_e1rm,
        max(case when exercise_name = '{{ var("bench_exercise_name") }}' then running_max_e1rm end)
            as bench_e1rm,
        max(
            case when exercise_name = '{{ var("deadlift_exercise_name") }}' then running_max_e1rm end
        ) as deadlift_e1rm
    from running_max
    group by workout_date
),

forward_filled as (
    select
        workout_date,
        last_value(squat_e1rm ignore nulls) over (
            order by workout_date
            rows between unbounded preceding and current row
        ) as squat_e1rm,
        last_value(bench_e1rm ignore nulls) over (
            order by workout_date
            rows between unbounded preceding and current row
        ) as bench_e1rm,
        last_value(deadlift_e1rm ignore nulls) over (
            order by workout_date
            rows between unbounded preceding and current row
        ) as deadlift_e1rm
    from pivoted
)

select
    workout_date,
    squat_e1rm,
    bench_e1rm,
    deadlift_e1rm,
    round(squat_e1rm + bench_e1rm + deadlift_e1rm, 1) as estimated_total
from forward_filled
where
    squat_e1rm is not null
    and bench_e1rm is not null
    and deadlift_e1rm is not null
order by workout_date
