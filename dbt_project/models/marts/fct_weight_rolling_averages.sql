{{
  config(
    materialized='external',
    location='s3://{{ var("s3_bucket") }}/transformed/fct_weight_rolling_averages'
  )
}}

-- Rolling weight averages at multiple windows
-- Grain: One row per date with a weight reading

with daily_weight as (
    select
        date,
        weight_kg
    from {{ ref('fct_daily_summary') }}
    where weight_kg is not null
),

rolling as (
    select
        date,
        weight_kg,
        round(avg(weight_kg) over (
            order by date rows between 6 preceding and current row
        ), 2) as avg_7d,
        round(avg(weight_kg) over (
            order by date rows between 13 preceding and current row
        ), 2) as avg_14d,
        round(avg(weight_kg) over (
            order by date rows between 29 preceding and current row
        ), 2) as avg_30d,
        round(avg(weight_kg) over (
            order by date rows between 59 preceding and current row
        ), 2) as avg_60d,
        round(avg(weight_kg) over (
            order by date rows between 119 preceding and current row
        ), 2) as avg_120d
    from daily_weight
)

select *
from rolling
order by date desc
