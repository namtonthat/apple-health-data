{{ config(materialized='table') }}

-- Track progression on each exercise over time
-- Shows personal records and trends

with sets as (
    select * from {{ ref('fct_workout_sets') }}
    where set_type = 'normal'  -- Only working sets
),

-- Daily best for each exercise
daily_best as (
    select
        workout_date,
        exercise_name,
        max(weight_kg) as best_weight_kg,
        max(reps) as best_reps,
        max(volume_kg) as best_set_volume_kg,
        sum(volume_kg) as total_volume_kg,
        count(*) as sets_performed,
        round(avg(rpe), 1) as avg_rpe
    from sets
    where weight_kg > 0
    group by workout_date, exercise_name
),

-- Calculate running PRs
with_prs as (
    select
        *,
        max(best_weight_kg) over (
            partition by exercise_name
            order by workout_date
            rows between unbounded preceding and current row
        ) as weight_pr_to_date,
        max(best_set_volume_kg) over (
            partition by exercise_name
            order by workout_date
            rows between unbounded preceding and current row
        ) as volume_pr_to_date
    from daily_best
),

-- Add PR flags and previous session comparison
final as (
    select
        workout_date,
        exercise_name,
        best_weight_kg,
        best_reps,
        best_set_volume_kg,
        total_volume_kg,
        sets_performed,
        avg_rpe,

        -- PR tracking
        weight_pr_to_date,
        volume_pr_to_date,
        case when best_weight_kg = weight_pr_to_date then true else false end as is_weight_pr,
        case when best_set_volume_kg = volume_pr_to_date then true else false end as is_volume_pr,

        -- Session comparison
        lag(best_weight_kg) over (partition by exercise_name order by workout_date) as prev_session_weight,
        lag(total_volume_kg) over (partition by exercise_name order by workout_date) as prev_session_volume,

        -- Exercise frequency
        row_number() over (partition by exercise_name order by workout_date) as session_number,
        count(*) over (partition by exercise_name) as total_sessions

    from with_prs
)

select * from final
order by exercise_name, workout_date desc
