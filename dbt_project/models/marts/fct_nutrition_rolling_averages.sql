{{
  config(
    materialized='external',
    location='s3://{{ var("s3_bucket") }}/transformed/fct_nutrition_rolling_averages'
  )
}}

-- Rolling macro averages over RECORDED days only.
-- Grain: one row per date that has logged nutrition. Days without any macro
-- logged are excluded entirely, so the rows-based windows average across the
-- last N *recorded* days (not the last N calendar days) — e.g. avg_7d is the
-- mean over the seven most recent days you actually tracked.

with daily_macros as (
    select
        date,
        protein_g,
        carbs_g,
        fat_g,
        logged_calories
    from {{ ref('fct_daily_summary') }}
    where coalesce(protein_g, carbs_g, fat_g) is not null
),

rolling as (
    select
        date,
        protein_g,
        carbs_g,
        fat_g,
        logged_calories,
        count(*) over (
            order by date rows between 6 preceding and current row
        ) as recorded_days_7d,
        round(avg(protein_g) over (
            order by date rows between 6 preceding and current row
        ), 0) as protein_avg_7d,
        round(avg(carbs_g) over (
            order by date rows between 6 preceding and current row
        ), 0) as carbs_avg_7d,
        round(avg(fat_g) over (
            order by date rows between 6 preceding and current row
        ), 0) as fat_avg_7d,
        round(avg(logged_calories) over (
            order by date rows between 6 preceding and current row
        ), 0) as calories_avg_7d,
        round(avg(protein_g) over (
            order by date rows between 29 preceding and current row
        ), 0) as protein_avg_30d,
        round(avg(carbs_g) over (
            order by date rows between 29 preceding and current row
        ), 0) as carbs_avg_30d,
        round(avg(fat_g) over (
            order by date rows between 29 preceding and current row
        ), 0) as fat_avg_30d,
        round(avg(logged_calories) over (
            order by date rows between 29 preceding and current row
        ), 0) as calories_avg_30d
    from daily_macros
)

select *
from rolling
order by date desc
