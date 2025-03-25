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
),

calories as (
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
),

in_bed as (
    select
        rs.metric_date,
        'in_bed' as metric_name,
        data_fields.inbed as quantity,
        rs.units
    from {{ ref('raw_sleep') }} as rs
),

asleep as (
    select
        rs.metric_date,
        'asleep' as metric_name,
        data_fields.asleep as quantity,
        rs.units
    from {{ ref('raw_sleep') }} as rs
),

deep as (
    select
        rs.metric_date,
        'deep_sleep' as metric_name,
        data_fields.deep as quantity,
        rs.units
    from {{ ref('raw_sleep') }} as rs
),

all_sleep_data as (
    select * from in_bed
    union all
    select * from asleep
    union all
    select * from deep
),

volume_data as (
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
union all

select
    asd.metric_date,
    asd.metric_name,
    round(asd.quantity, 1) as quantity,
    asd.units
from all_sleep_data as asd
union all
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
    cast(round(quantity, 1) as float) as quantity,
    units
from all_nutrition
union all
select
    metric_date,
    metric_name,
    round(quantity, 2) as quantity,
    units
from weight
order by metric_date desc, metric_name asc
