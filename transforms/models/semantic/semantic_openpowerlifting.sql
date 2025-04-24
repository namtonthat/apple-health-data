-- first filter down to the latest load
with base as (
    select
        metric_date,
        bodyweight_kg,
        weight_class_kg,
        squat1_kg,
        squat2_kg,
        squat3_kg,
        CAST(squat4_kg as DOUBLE) as squat4_kg,
        best3_squat_kg,
        bench1_kg,
        bench2_kg,
        bench3_kg,
        CAST(bench4_kg as DOUBLE) as bench4_kg,
        best3_bench_kg,
        deadlift1_kg,
        deadlift2_kg,
        deadlift3_kg,
        CAST(deadlift4_kg as DOUBLE) as deadlift4_kg,
        best3_deadlift_kg,
        total_kg
    from {{ ref('raw_openpowerlifting') }}
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
