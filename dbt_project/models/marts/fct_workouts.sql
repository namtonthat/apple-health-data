{{
  config(
    materialized='external',
    location='s3://{{ var("s3_bucket") }}/transformed/fct_workouts'
  )
}}

-- Fact table: one row per workout (session grain)
-- Sits between fct_workout_sets (set grain) and fct_daily_summary (day grain).
-- Aggregates set-level facts up to the session so the dashboard reads a clean
-- one-row-per-workout table instead of GROUP BY-ing the set table at query time.

with sets as (
    select * from {{ ref('fct_workout_sets') }}
),

final as (
    select
        -- Identity / context
        workout_id,
        workout_date,
        day_name,
        start_hour,
        started_at,
        ended_at,
        workout_name,
        workout_duration_minutes,

        -- Session aggregates
        count(distinct exercise_name) as unique_exercises,
        count(*) as total_sets,
        sum(case when set_type = 'normal' then 1 else 0 end) as working_sets,
        sum(reps) as total_reps,
        round(sum(volume_kg), 0) as total_volume_kg,
        max(weight_kg) as max_weight_kg,
        round(avg(case when rpe > 0 then rpe end), 1) as avg_rpe

    from sets
    group by
        workout_id,
        workout_date,
        day_name,
        start_hour,
        started_at,
        ended_at,
        workout_name,
        workout_duration_minutes
)

select * from final
order by started_at desc
