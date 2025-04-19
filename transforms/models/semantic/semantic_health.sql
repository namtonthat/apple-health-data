-- Use CTEs to reuse subqueries
with raw_metrics as (
    select * from {{ ref('raw_latest_api_metrics') }}
),

raw_nutrition as (
    select * from {{ ref('raw_nutrition') }}
),

activity as (
    select *
    from raw_metrics
    where
        metric_name in ('step_count', 'mindful_minutes', 'apple_exercise_time')
),

weight as (
    select *
    from raw_metrics
    where metric_name = 'weight_body_mass'
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
    from raw_nutrition
    group by metric_date
),

detailed_calories as (
    select
        metric_date,
        case
            when metric_name = 'carbohydrates' then 'calories_carbohydrates'
            when metric_name = 'protein' then 'calories_protein'
            when metric_name = 'total_fat' then 'calories_fat'
        end as metric_name,
        case
            when metric_name = 'carbohydrates' then quantity * 4
            when metric_name = 'protein' then quantity * 4
            when metric_name = 'total_fat' then quantity * 9
        end as quantity,
        'kcal' as units
    from raw_nutrition
    where metric_name in ('carbohydrates', 'protein', 'total_fat')
),

all_nutrition as (
    select * from calories
    where quantity != 0
    union all
    select * from detailed_calories
    where quantity != 0
    union all
    select * from raw_nutrition
),

all_sleep_data as (
    select
        rs.metric_date,
        sleep_type.metric_name,
        sleep_type.quantity,
        rs.units
    from {{ ref('raw_sleep') }} as rs
    cross join lateral (
        values
        ('in_bed', data_fields.inbed),
        ('asleep', data_fields.asleep),
        ('deep_sleep', data_fields.deep)
    ) as sleep_type (metric_name, quantity)
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
    group by
        id, index, metric_date, start_time, exercise_name, workout_duration_mins
),

total_workout_volume as (
    select
        metric_date,
        start_time,
        'workout_volume' as metric_name,
        sum(volume_kg) as quantity,
        'kg' as units
    from volume_data
    group by metric_date, start_time
),

total_time as (
    select
        id,
        metric_date,
        'workout_time' as metric_name,
        workout_duration_mins as quantity,
        'mins' as units
    from volume_data
),

-- Final unified metrics output
final_metrics as (
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
        metric_date,
        metric_name,
        round(quantity, 1) as quantity,
        units
    from all_sleep_data
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
)

select *
from final_metrics
order by metric_date desc, metric_name asc
