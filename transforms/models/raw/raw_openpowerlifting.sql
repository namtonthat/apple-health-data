with latest_load_date as (
    select MAX(ctrl_load_date) as max_ctrl_load_date
    from {{ ref('stg_openpowerlifting') }}
),

-- first filter down to the latest load
base as (
    select
        opl.metric_date,
        opl.bodyweight_kg,
        opl.weight_class_kg,
        opl.squat1_kg,
        opl.squat2_kg,
        opl.squat3_kg,
        CAST(opl.squat4_kg as DOUBLE) as squat4_kg,
        opl.best3_squat_kg,
        opl.bench1_kg,
        opl.bench2_kg,
        opl.bench3_kg,
        CAST(opl.bench4_kg as DOUBLE) as bench4_kg,
        opl.best3_bench_kg,
        opl.deadlift1_kg,
        opl.deadlift2_kg,
        opl.deadlift3_kg,
        CAST(opl.deadlift4_kg as DOUBLE) as deadlift4_kg,
        opl.best3_deadlift_kg,
        opl.total_kg
    from {{ ref('stg_openpowerlifting') }} as opl
    inner join latest_load_date as l
        on opl.ctrl_load_date = l.max_ctrl_load_date
)

select
    metric_date,
    metric_name,
    value_kg as quantity,
    'kg' as units
from base 
UNPIVOT(
  value_kg FOR metric_name IN (
    bodyweight_kg,
    weight_class_kg,
    squat1_kg,
    squat2_kg,
    squat3_kg,
    squat4_kg,
    best3_squat_kg,
    bench1_kg,
    bench2_kg,
    bench3_kg,
    bench4_kg,
    best3_bench_kg,
    deadlift1_kg,
    deadlift2_kg,
    deadlift3_kg,
    deadlift4_kg,
    best3_deadlift_kg,
total_kg,
  )
) AS unpvt
