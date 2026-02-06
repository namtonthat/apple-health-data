{{
  config(
    materialized='external',
    location='s3://{{ var("s3_bucket") }}/transformed/fct_daily_summary'
  )
}}

-- Combined daily summary: Health vitals, activity, nutrition, and workouts
-- Grain: One row per calendar day

with vitals as (
    select * from {{ ref('int_health__daily_vitals') }}
),

activity as (
    select * from {{ ref('int_health__daily_activity') }}
),

nutrition as (
    select * from {{ ref('int_health__daily_nutrition') }}
),

workouts as (
    select * from {{ ref('int_hevy__daily_workouts') }}
),

-- Generate date spine from all sources
all_dates as (
    select distinct metric_date as date from vitals
    union
    select distinct metric_date as date from activity
    union
    select distinct metric_date as date from nutrition
    union
    select distinct workout_date as date from workouts
),

final as (
    select
        d.date,

        -- Body composition
        v.weight_kg,
        v.bmi,

        -- Cardiovascular health
        v.resting_hr_bpm,
        v.hrv_ms,
        v.vo2_max,
        v.blood_oxygen_pct,

        -- Sleep
        round(v.sleep_total_hours, 1) as sleep_hours,
        round(v.sleep_deep_hours, 1) as sleep_deep_hours,
        round(v.sleep_rem_hours, 1) as sleep_rem_hours,
        round(v.sleep_core_hours, 1) as sleep_light_hours,

        -- Daily activity
        a.steps,
        a.flights_climbed,
        round(a.distance_km, 2) as distance_km,
        round(a.active_calories, 0) as active_calories,
        round(a.basal_calories, 0) as basal_calories,
        a.exercise_minutes,
        a.stand_hours,
        a.daylight_minutes,

        -- Nutrition / Macros
        round(n.protein_g, 0) as protein_g,
        round(n.carbs_g, 0) as carbs_g,
        round(n.fat_g, 0) as fat_g,
        round(n.fiber_g, 0) as fiber_g,
        round(n.water_ml, 0) as water_ml,

        -- Calories: calculated (Apple Watch) vs logged (MacroFactor)
        round(coalesce(a.active_calories, 0) + coalesce(a.basal_calories, 0), 0) as calculated_calories,
        round(n.dietary_calories, 0) as logged_calories,
        round(greatest(
            coalesce(a.active_calories, 0) + coalesce(a.basal_calories, 0),
            coalesce(n.dietary_calories, 0)
        ), 0) as total_calories,

        -- Workout summary
        coalesce(w.workouts, 0) as workouts,
        w.unique_exercises,
        w.total_sets,
        w.working_sets,
        w.total_reps,
        round(w.total_volume_kg, 0) as total_volume_kg,
        w.max_weight_kg,
        w.avg_rpe,
        w.total_duration_minutes as workout_duration_minutes,

        -- Derived flags
        case when w.workout_date is not null then true else false end as had_strength_workout,
        w.day_name

    from all_dates d
    left join vitals v on d.date = v.metric_date
    left join activity a on d.date = a.metric_date
    left join nutrition n on d.date = n.metric_date
    left join workouts w on d.date = w.workout_date
)

select * from final
order by date desc
