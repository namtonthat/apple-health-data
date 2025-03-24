with volume_data as (
    select
        id,
        index,
        metric_date,
        start_time,
        exercise_name,
        workout_duration_mins,
        sum(weight_kg * reps) as volume_kg
    from {{ ref('semantic_exercises') }}
    group by all
    order by start_time desc, index asc
),

total_workout_volume as (
    select
        metric_date,
        start_time,
        'workout_volume' as metric_name,
        sum(volume_kg) as quantity,
        'kg' as units
    from volume_data
    group by all
    order by start_time desc
),

total_time as (
    select distinct
        id,
        metric_date,
        'workout_time' as metric_name,
        workout_duration_mins as quantity,
        'mins' as units
    from volume_data
)

select
    metric_date,
    metric_name,
    quantity,
    units
from total_workout_volume
union all
select
    metric_date,
    metric_name,
    quantity,
    units
from total_time
