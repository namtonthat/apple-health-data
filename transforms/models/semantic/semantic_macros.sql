with macros as (
    select *
    from {{ ref('raw_api_metrics') }}
    where metric_name in (
        'carbohydrates',
        'fiber',
        'protein',
        'total_fat'
    )
)

select * from macros
