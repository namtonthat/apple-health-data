{{ config(materialized='view') }}

-- Aggregate workout data to one row per day
with workouts as (
    select * from {{ ref('stg_hevy__workouts') }}
),

exercises as (
    select * from {{ ref('stg_hevy__exercises') }}
),

sets as (
    select * from {{ ref('stg_hevy__sets') }}
),

-- Join sets to exercises to workouts
set_details as (
    select
        w.workout_date,
        w.workout_id,
        w.workout_name,
        w.duration_minutes,
        w.day_name,
        e.exercise_name,
        s.set_number,
        s.set_type,
        s.weight_kg,
        s.reps,
        s.rpe
    from sets s
    inner join exercises e on s.exercise_id = e.exercise_id
    inner join workouts w on e.workout_id = w.workout_id
),

-- Aggregate to daily level
daily_summary as (
    select
        workout_date,
        day_name,

        -- Workout count & duration
        count(distinct workout_id) as workouts,
        sum(distinct duration_minutes) as total_duration_minutes,

        -- Exercise stats
        count(distinct exercise_name) as unique_exercises,

        -- Set stats
        count(*) as total_sets,
        sum(case when set_type = 'normal' then 1 else 0 end) as working_sets,
        sum(case when set_type = 'warmup' then 1 else 0 end) as warmup_sets,

        -- Volume metrics
        sum(reps) as total_reps,
        sum(weight_kg * reps) as total_volume_kg,
        max(weight_kg) as max_weight_kg,

        -- RPE
        round(avg(case when rpe > 0 then rpe end), 1) as avg_rpe

    from set_details
    group by workout_date, day_name
)

select * from daily_summary
