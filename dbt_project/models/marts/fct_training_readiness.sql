{{
  config(
    materialized='external',
    location='s3://{{ var("s3_bucket") }}/transformed/fct_training_readiness'
  )
}}

-- Training readiness score: composite of HRV, RHR, sleep, and deep sleep
-- Each component scored 0–25 based on z-score against 30-day rolling baseline
-- Grain: One row per date with at least one input metric

with daily as (
    select
        date,
        hrv_ms,
        resting_hr_bpm,
        sleep_hours,
        case
            when sleep_hours > 0 then sleep_deep_hours / sleep_hours
        end as deep_sleep_ratio
    from {{ ref('fct_daily_summary') }}
    where
        hrv_ms is not null
        or resting_hr_bpm is not null
        or sleep_hours is not null
),

stats as (
    select
        date,
        hrv_ms,
        resting_hr_bpm,
        sleep_hours,
        deep_sleep_ratio,
        avg(hrv_ms) over (
            order by date rows between 29 preceding and current row
        ) as hrv_avg_30d,
        stddev(hrv_ms) over (
            order by date rows between 29 preceding and current row
        ) as hrv_std_30d,
        avg(resting_hr_bpm) over (
            order by date rows between 29 preceding and current row
        ) as rhr_avg_30d,
        stddev(resting_hr_bpm) over (
            order by date rows between 29 preceding and current row
        ) as rhr_std_30d,
        avg(sleep_hours) over (
            order by date rows between 29 preceding and current row
        ) as sleep_avg_30d,
        avg(deep_sleep_ratio) over (
            order by date rows between 29 preceding and current row
        ) as deep_avg_30d
    from daily
),

scored as (
    select
        date,
        hrv_ms,
        resting_hr_bpm,
        sleep_hours,
        deep_sleep_ratio,
        case
            when hrv_ms is null or hrv_std_30d is null or hrv_std_30d = 0 then null
            else round(least(greatest(
                (hrv_ms - hrv_avg_30d) / hrv_std_30d,
                -2
            ), 2) * 6.25 + 12.5)
        end as hrv_score,
        case
            when resting_hr_bpm is null or rhr_std_30d is null or rhr_std_30d = 0 then null
            else round(least(greatest(
                -(resting_hr_bpm - rhr_avg_30d) / rhr_std_30d,
                -2
            ), 2) * 6.25 + 12.5)
        end as rhr_score,
        case
            when sleep_hours is null then null
            else round(least(sleep_hours / 7.0, 1.0) * 25)
        end as sleep_score,
        case
            when deep_sleep_ratio is null or deep_avg_30d is null or deep_avg_30d = 0 then null
            else round(least(deep_sleep_ratio / deep_avg_30d, 1.5) / 1.5 * 25)
        end as deep_score
    from stats
)

select
    date,
    hrv_ms,
    resting_hr_bpm,
    sleep_hours,
    round(deep_sleep_ratio, 3) as deep_sleep_ratio,
    hrv_score,
    rhr_score,
    sleep_score,
    deep_score,
    coalesce(hrv_score, 0) + coalesce(rhr_score, 0) + coalesce(sleep_score, 0) + coalesce(deep_score, 0) as readiness_score
from scored
order by date desc
