-- Fail when the estimated total is not the sum of the Big 3 components.

select
    workout_date,
    squat_e1rm,
    bench_e1rm,
    deadlift_e1rm,
    estimated_total
from {{ ref('fct_e1rm_rolling_total') }}
where
    squat_e1rm is not null
    and bench_e1rm is not null
    and deadlift_e1rm is not null
    and estimated_total != round(squat_e1rm + bench_e1rm + deadlift_e1rm, 1)
