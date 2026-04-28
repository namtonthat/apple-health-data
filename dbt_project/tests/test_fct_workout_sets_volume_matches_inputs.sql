-- Fail when volume_kg does not match weight_kg * reps for strength sets.

select
    set_id,
    weight_kg,
    reps,
    volume_kg
from {{ ref('fct_workout_sets') }}
where
    weight_kg is not null
    and reps is not null
    and volume_kg is not null
    and round(weight_kg * reps, 1) != volume_kg
