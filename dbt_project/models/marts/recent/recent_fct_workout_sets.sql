{{
  config(
    materialized='external',
    location='s3://{{ var("s3_bucket") }}/transformed/recent/fct_workout_sets'
  )
}}

-- Last 365 days of workout sets for fast dashboard reads
-- Grain: One row per set (truncated to 1 year)

select *
from {{ ref('fct_workout_sets') }}
where workout_date >= (now() at time zone '{{ var("timezone") }}')::date - interval '365 days'
order by workout_date desc, started_at desc, exercise_order asc, set_number asc
