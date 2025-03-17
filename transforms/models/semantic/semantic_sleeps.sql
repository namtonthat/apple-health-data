with sleep_metrics as (
    select
        metric_date,
        SUM(case when metric_name = 'asleep' then quantity else 0 end)
            as asleep,
        SUM(case when metric_name = 'in_bed' then quantity else 0 end)
            as in_bed,
        SUM(case when metric_name = 'deep_sleep' then quantity else 0 end)
            as deep_sleep
    from {{ ref('semantic_sleep') }}
    group by metric_date
),

bedtime as (
    select
        metric_date,
        MAX(case when metric_name = 'sleep_start' then sleep_times end)
            as sleep_start
    from {{ ref('semantic_sleep_times') }}
    group by metric_date
),

aggregated as (
    select
        m.metric_date,
        m.asleep,
        m.in_bed,
        m.deep_sleep,
        ROUND((m.asleep / NULLIF(m.in_bed, 0) * 100), 0) as efficiency,
        b.sleep_start
    from sleep_metrics as m
    left join bedtime as b
        on m.metric_date = b.metric_date
)

-- Unpivot the aggregated data into one row per metric.
select
    metric_date,
    'asleep' as metric_name,
    asleep as quantity,
    'hr' as units
from aggregated
union all
select
    metric_date,
    'in_bed' as metric_name,
    in_bed as quantity,
    'hr' as units
from aggregated
union all
select
    metric_date,
    'deep_sleep' as metric_name,
    deep_sleep as quantity,
    'hr' as units
from aggregated
union all
select
    metric_date,
    'efficiency' as metric_name,
    efficiency as quantity,
    '%' as units
from aggregated
union all
-- SELECT metric_date, 'in_bed_time' AS metric_name, sleep_start AS quantity,
-- '%' AS units,
-- FROM aggregated
select
    metric_date,
    'in_bed_time' as metric_name,
    -- Compute the bedtime as a number: 
    -- the 12-hour clock hour plus minutes as fraction.
    ROUND(
        CAST(STRFTIME(sleep_start, '%I') as DOUBLE)
        + (CAST(STRFTIME(sleep_start, '%M') as DOUBLE) / 60.0),
        2
    ) as quantity,
    -- Units is the period (AM or PM)
    STRFTIME(sleep_start, '%p') as units
from aggregated
order by metric_date desc, metric_name asc
