with calories as (
    select
        metric_date,
        'calories' as metric_name,
        'g' as units,
        round(sum(
            case
                when metric_name = 'carbohydrates' then quantity * 4
                when metric_name = 'protein' then quantity * 4
                when metric_name = 'total_fat' then quantity * 9
                else 0
            end
        ), 2) as quantity
    from {{ ref('raw_macros') }}
    group by all
)

select * from calories
union all
select * from {{ ref('raw_macros') }}
order by metric_date desc, metric_name asc
