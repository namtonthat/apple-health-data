{{ config(materialized='view') }}

-- Pivot health metrics into one row per day with activity data
with metrics as (
    select * from {{ ref('stg_health__metrics') }}
),

pivoted as (
    select
        metric_date,

        -- Steps & movement
        max(case when metric_name = 'step_count' then value end) as steps,
        max(case when metric_name = 'flights_climbed' then value end) as flights_climbed,
        max(case when metric_name = 'walking_running_distance' then value end) as distance_km,

        -- Energy
        max(case when metric_name = 'active_energy' then value end) as active_calories,
        max(case when metric_name = 'basal_energy_burned' then value / 4.184 end) as basal_calories,  -- kJ to kcal

        -- Apple activity rings
        max(case when metric_name = 'apple_exercise_time' then value end) as exercise_minutes,
        max(case when metric_name = 'apple_stand_time' then value end) as stand_minutes,
        max(case when metric_name = 'apple_stand_hour' then value end) as stand_hours,

        -- Walking metrics
        max(case when metric_name = 'walking_speed' then value end) as walking_speed_kmh,
        max(case when metric_name = 'walking_step_length' then value end) as step_length_cm,
        max(case when metric_name = 'walking_asymmetry_percentage' then value end) as walking_asymmetry_pct,
        max(case when metric_name = 'walking_double_support_percentage' then value end) as double_support_pct,

        -- Stair metrics
        max(case when metric_name = 'stair_speed_up' then value end) as stair_speed_up_ms,
        max(case when metric_name = 'stair_speed_down' then value end) as stair_speed_down_ms,

        -- Environmental
        max(case when metric_name = 'time_in_daylight' then value end) as daylight_minutes

    from metrics
    group by metric_date
)

select * from pivoted
