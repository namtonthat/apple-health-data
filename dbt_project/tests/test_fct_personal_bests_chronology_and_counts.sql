-- Fail when aggregate competition metadata is internally inconsistent.

select
    athlete_name,
    total_competitions,
    first_competition,
    last_competition
from {{ ref('fct_personal_bests') }}
where
    total_competitions < 1
    or first_competition is null
    or last_competition is null
    or first_competition > last_competition
