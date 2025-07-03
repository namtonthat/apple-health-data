{{ config(materialized='view') }}

-- Extract nutrition metrics from the unified semantic_health model
select
    metric_date,
    metric_name,
    quantity,
    units
from {{ ref('semantic_health') }}
where metric_name in (
    'carbohydrates',
    'protein',
    'total_fat',
    'calories',
    'calories_carbohydrates',
    'calories_protein',
    'calories_fat'
)
