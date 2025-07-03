{{ config(materialized='view') }}

-- Extract activity metrics from the unified semantic_health model
select
    metric_date,
    metric_name,
    quantity,
    units
from {{ ref('semantic_health') }}
where metric_name in (
    'step_count',
    'mindful_minutes',
    'apple_exercise_time'
)
