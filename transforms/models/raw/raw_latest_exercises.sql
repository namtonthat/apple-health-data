-- with ranked as (
--     select
--          *,
--          row_number() over (partition by id order by ctrl_load_date desc) as rn
--     from {{ ref('raw_exercises')}}
-- )
with latest_dates as (
    select 
        id,
        max(ctrl_load_date) as latest_ctrl_load_date
    from {{ ref('raw_exercises')}}
    group by id
)

select
    f.id,
    f.workout_name,
    f.start_time,
    f.end_time, 
    f.updated_at,
    f.created_at,
    f.end_time - start_time as workout_duration_minutes,
    f.index,
    f.workout_name,
    f.exercise_name,
    f.notes,
    f.set_type,
    f.weight_kg,
    f.reps,
    f.rpe,
  f.ctrl_load_date
  from {{ ref('raw_exercises')}} f
inner join latest_dates ld
    on f.id = ld.id
   and f.ctrl_load_date = ld.latest_ctrl_load_date
-- from ranked 
-- where rn = 1
