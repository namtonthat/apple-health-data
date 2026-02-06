{{
  config(
    materialized='external',
    location='s3://{{ var("s3_bucket") }}/transformed/fct_workout_sets'
  )
}}

-- Fact table: Individual workout sets with full context
-- Grain: One row per set

with workouts as (
    select * from {{ ref('stg_hevy__workouts') }}
),

exercises as (
    select * from {{ ref('stg_hevy__exercises') }}
),

sets as (
    select * from {{ ref('stg_hevy__sets') }}
),

final as (
    select
        -- IDs
        s.set_id,
        e.exercise_id,
        w.workout_id,

        -- Date/time dimensions
        w.workout_date::date as workout_date,
        w.day_name,
        w.start_hour,
        w.started_at,
        w.ended_at,

        -- Workout context
        w.workout_name,
        w.duration_minutes as workout_duration_minutes,

        -- Exercise context
        e.exercise_name,
        e.exercise_order,
        e.superset_id,
        e.notes as exercise_notes,

        -- Set details
        s.set_number,
        s.set_type,

        -- Performance metrics
        s.weight_kg,
        s.reps,
        s.rpe,
        round(s.weight_kg * s.reps, 1) as volume_kg,

        -- Cardio metrics
        s.distance_meters,
        s.duration_seconds

    from sets s
    inner join exercises e on s.exercise_id = e.exercise_id
    inner join workouts w on e.workout_id = w.workout_id
    where s.weight_kg is not null or s.reps is not null or s.distance_meters is not null
)

select * from final
order by workout_date desc, started_at desc, exercise_order, set_number
