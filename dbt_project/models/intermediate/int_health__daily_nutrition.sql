{{ config(materialized='view') }}

-- Pivot dietary/nutrition metrics into one row per day
with metrics as (
    select * from {{ ref('stg_health__metrics') }}
),

pivoted as (
    select
        metric_date,

        -- Macronutrients (common Apple Health metric names)
        max(case when metric_name = 'dietary_protein' then value end) as protein_g,
        max(case when metric_name = 'dietary_carbohydrates' then value end) as carbs_g,
        max(case when metric_name = 'dietary_fat_total' then value end) as fat_g,
        max(case when metric_name = 'dietary_fiber' then value end) as fiber_g,
        max(case when metric_name = 'dietary_sugar' then value end) as sugar_g,

        -- Calories from food
        max(case when metric_name = 'dietary_energy' then value end) as dietary_calories,

        -- Micronutrients (if tracked)
        max(case when metric_name = 'dietary_sodium' then value end) as sodium_mg,
        max(case when metric_name = 'dietary_cholesterol' then value end) as cholesterol_mg,

        -- Water
        max(case when metric_name = 'dietary_water' then value end) as water_ml

    from metrics
    group by metric_date
)

select * from pivoted
