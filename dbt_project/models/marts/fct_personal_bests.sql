{{
  config(
    materialized='external',
    location='s3://{{ var("s3_bucket") }}/transformed/fct_personal_bests'
  )
}}

-- Personal bests from competition history
-- Grain: One row per athlete (currently single athlete)

with competitions as (
    select * from {{ ref('stg_openpowerlifting__competitions') }}
),

personal_bests as (
    select
        athlete_name,

        -- Best lifts across all competitions
        max(squat_kg) as squat_pr_kg,
        max(bench_kg) as bench_pr_kg,
        max(deadlift_kg) as deadlift_pr_kg,
        max(total_kg) as total_pr_kg,

        -- Best scores
        max(dots_score) as best_dots,
        max(wilks_score) as best_wilks,

        -- Competition stats
        count(*) as total_competitions,
        min(competition_date) as first_competition,
        max(competition_date) as last_competition,

        -- Best placing
        min(place::int) as best_place

    from competitions
    group by athlete_name
)

select * from personal_bests
