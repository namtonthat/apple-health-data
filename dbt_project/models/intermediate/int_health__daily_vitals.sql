{{ config(materialized='view') }}

-- Pivot health metrics into one row per day with key vital signs
with metrics as (
    select * from {{ ref('stg_health__metrics') }}
),

pivoted as (
    select
        metric_date,

        -- Body composition
        max(case when metric_name = 'weight_body_mass' then value end) as weight_kg,
        max(case when metric_name = 'body_mass_index' then value end) as bmi,

        -- Cardiovascular
        max(case when metric_name = 'resting_heart_rate' then value end) as resting_hr_bpm,
        max(case when metric_name = 'walking_heart_rate_average' then value end) as walking_hr_bpm,
        max(case when metric_name = 'heart_rate_variability' then value end) as hrv_ms,
        max(case when metric_name = 'vo2_max' then value end) as vo2_max,
        max(case when metric_name = 'blood_oxygen_saturation' then value end) as blood_oxygen_pct,

        -- Sleep (total = rem + deep + core)
        max(case when metric_name = 'sleep_analysis' then sleep_rem_hours end) as sleep_rem_hours,
        max(case when metric_name = 'sleep_analysis' then sleep_deep_hours end) as sleep_deep_hours,
        max(case when metric_name = 'sleep_analysis' then sleep_core_hours end) as sleep_core_hours,
        max(case when metric_name = 'sleep_analysis' then sleep_awake_hours end) as sleep_awake_hours,
        max(case
            when metric_name = 'sleep_analysis'
                then coalesce(sleep_rem_hours, 0) + coalesce(sleep_deep_hours, 0) + coalesce(sleep_core_hours, 0)
        end) as sleep_total_hours,

        -- Respiratory
        max(case when metric_name = 'respiratory_rate' then value end) as respiratory_rate

        -- Heart rate (uncomment to enable):
        -- max(case when metric_name = 'heart_rate' then value end) as avg_hr_bpm,

        -- Audio exposure (uncomment to enable):
        -- max(case when metric_name = 'environmental_audio_exposure' then value end) as env_audio_exposure_db,
        -- max(case when metric_name = 'headphone_audio_exposure' then value end) as headphone_audio_exposure_db

    from metrics
    group by metric_date
)

select * from pivoted
