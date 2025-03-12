with activity as (
    select *
    from {{ ref('raw_api_metrics') }}
    where metric_name in (
        'step_count',
        'mindful_minutes',
        'apple_exercise_time',
        'weight_body_mass'
    )
)

select * from activity
