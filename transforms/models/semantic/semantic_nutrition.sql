with calories as (
    select
        metric_date,
        'calories' as metric_name,
        sum(
            case
                when metric_name = 'carbohydrates' then quantity * 4
                when metric_name = 'protein' then quantity * 4
                when metric_name = 'total_fat' then quantity * 9
                else 0
            end
        ) as quantity,
        'kcal' as units
    from {{ ref('raw_nutrition') }}
    group by all
),

all_nutrition as (
    select * from calories
    where quantity != 0
    union all
    select * from {{ ref('raw_nutrition') }}
)

select
    metric_date,
    metric_name,
    cast(round(quantity, 1) as float) as quantity,
    units
from all_nutrition
order by metric_date desc, metric_name asc
