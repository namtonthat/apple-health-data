with unnested_data as (
    select
        se.*,
        unnest(se.exercises, recursive := true) -- noqa: AL03
    from {{ ref('stg_exercises') }} as se
    {% if is_incremental() %}
        where se.start_time >= current_date - interval '15' day
    {% endif %}
),

unnested_exercise_data as (
    select
        ud.*,
        unnest(ud.sets).type as set_type,
        unnest(ud.sets).weight_kg as weight_kg,
        unnest(ud.sets).reps as reps,
        unnest(ud.sets).rpe as rpe
    from unnested_data as ud
)

select
    id,
    title as workout_name,
    start_time,
    end_time,
    updated_at,
    created_at,
    end_time - start_time as workout_duration,
    index,
    title_1 as exercise_name,
    notes,
    set_type,
    weight_kg,
    reps,
    rpe,
    ctrl_load_date
from unnested_exercise_data
