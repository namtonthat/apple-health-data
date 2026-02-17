{{ config(materialized='view') }}

-- Pivot dietary/nutrition metrics into one row per day
-- Metric names match Apple Health export format
with metrics as (
    select * from {{ ref('stg_health__metrics') }}
),

pivoted as (
    select
        metric_date,

        -- Macronutrients
        max(case when metric_name = 'protein' then value end) as protein_g,
        max(case when metric_name = 'carbohydrates' then value end) as carbs_g,
        max(case when metric_name = 'total_fat' then value end) as fat_g,
        max(case when metric_name = 'fiber' then value end) as fiber_g,
        max(case when metric_name = 'dietary_sugar' then value end) as sugar_g,

        -- Fat breakdown
        max(case when metric_name = 'saturated_fat' then value end) as saturated_fat_g,
        max(case when metric_name = 'monounsaturated_fat' then value end) as monounsaturated_fat_g,
        max(case when metric_name = 'polyunsaturated_fat' then value end) as polyunsaturated_fat_g,

        -- Calories from food (convert kJ to kcal: 1 kJ = 0.239 kcal)
        max(case when metric_name = 'dietary_energy' then value * 0.239 end) as dietary_calories,

        -- Micronutrients
        max(case when metric_name = 'sodium' then value end) as sodium_mg,
        max(case when metric_name = 'cholesterol' then value end) as cholesterol_mg,
        max(case when metric_name = 'calcium' then value end) as calcium_mg,
        max(case when metric_name = 'iron' then value end) as iron_mg,
        max(case when metric_name = 'potassium' then value end) as potassium_mg,
        max(case when metric_name = 'magnesium' then value end) as magnesium_mg,
        max(case when metric_name = 'zinc' then value end) as zinc_mg,

        -- Vitamins
        max(case when metric_name = 'vitamin_a' then value end) as vitamin_a_mcg,
        max(case when metric_name = 'vitamin_c' then value end) as vitamin_c_mg,
        max(case when metric_name = 'vitamin_d' then value end) as vitamin_d_mcg,
        max(case when metric_name = 'vitamin_b12' then value end) as vitamin_b12_mcg,

        -- Water
        max(case when metric_name = 'dietary_water' then value end) as water_ml

        -- Additional vitamins (uncomment to enable):
        -- max(case when metric_name = 'vitamin_b6' then value end) as vitamin_b6_mg,
        -- max(case when metric_name = 'vitamin_e' then value end) as vitamin_e_mg,
        -- max(case when metric_name = 'vitamin_k' then value end) as vitamin_k_mcg,
        -- max(case when metric_name = 'thiamin' then value end) as thiamin_mg,          -- B1
        -- max(case when metric_name = 'riboflavin' then value end) as riboflavin_mg,      -- B2
        -- max(case when metric_name = 'niacin' then value end) as niacin_mg,              -- B3
        -- max(case when metric_name = 'pantothenic_acid' then value end) as pantothenic_acid_mg,  -- B5

        -- Additional minerals (uncomment to enable):
        -- max(case when metric_name = 'copper' then value end) as copper_mg,
        -- max(case when metric_name = 'manganese' then value end) as manganese_mg,
        -- max(case when metric_name = 'selenium' then value end) as selenium_mcg

    from metrics
    group by metric_date
)

select * from pivoted
