{{
  config(
    materialized='external',
    location='s3://{{ var("s3_bucket") }}/transformed/fct_exercise_progress'
  )
}}

-- Track progression on each exercise over time
-- Shows personal records and trends

with sets as (
    select * from {{ ref('fct_workout_sets') }}
    where set_type = 'normal'  -- Only working sets
),

-- Heaviest working set per day, carrying the reps performed AT that set.
-- Ranking by weight (then reps) so best_reps reflects the top-weight set rather
-- than the day's max reps across all sets — a heavy single + lighter back-off
-- sets must report the single's reps, not the back-offs'.
top_set as (
    select
        workout_date,
        exercise_name,
        weight_kg as best_weight_kg,
        reps as best_reps
    from (
        select
            workout_date,
            exercise_name,
            weight_kg,
            reps,
            row_number() over (
                partition by workout_date, exercise_name
                order by weight_kg desc, reps desc
            ) as rn
        from sets
        where weight_kg > 0
    ) ranked_sets
    where rn = 1
),

-- Daily aggregates across all working sets for that exercise
daily_agg as (
    select
        workout_date,
        exercise_name,
        max(volume_kg) as best_set_volume_kg,
        sum(volume_kg) as total_volume_kg,
        count(*) as sets_performed,
        round(avg(rpe), 1) as avg_rpe
    from sets
    where weight_kg > 0
    group by workout_date, exercise_name
),

-- Daily best for each exercise: top set joined to the day's aggregates
daily_best as (
    select
        top_set.workout_date,
        top_set.exercise_name,
        top_set.best_weight_kg,
        top_set.best_reps,
        daily_agg.best_set_volume_kg,
        daily_agg.total_volume_kg,
        daily_agg.sets_performed,
        daily_agg.avg_rpe
    from top_set
    inner join daily_agg
        on
            top_set.workout_date = daily_agg.workout_date
            and top_set.exercise_name = daily_agg.exercise_name
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
        coalesce(best_weight_kg = weight_pr_to_date, false) as is_weight_pr,
        coalesce(best_set_volume_kg = volume_pr_to_date, false) as is_volume_pr,

        -- Session comparison
        lag(best_weight_kg) over (
            partition by exercise_name
            order by workout_date
        ) as prev_session_weight,
        lag(total_volume_kg) over (
            partition by exercise_name
            order by workout_date
        ) as prev_session_volume,

        -- Exercise frequency
        row_number() over (
            partition by exercise_name
            order by workout_date
        ) as session_number,
        count(*) over (partition by exercise_name) as total_sessions

    from with_prs
)

select * from final
order by exercise_name asc, workout_date desc
