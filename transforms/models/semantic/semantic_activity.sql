with activity as (
    select *
    from {{ ref('raw_latest_api_metrics') }}
    where metric_name in (
        'step_count',
        'mindful_minutes',
        'apple_exercise_time'
    )
),

weight as (
    select *
    from {{ ref('raw_latest_api_metrics') }}
    where metric_name in (
        'weight_body_mass'
    )
)

select
    metric_date,
    metric_name,
    round(quantity, 0) as quantity,
    units
from activity
union all
select
    metric_date,
    metric_name,
    round(quantity, 2) as quantity,
    units
from weight
order by metric_date desc, metric_name asc
