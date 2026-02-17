{{
  config(
    materialized='external',
    location='s3://{{ var("s3_bucket") }}/transformed/recent/fct_strava_activities'
  )
}}

-- Last 365 days of Strava activities for fast dashboard reads
-- Grain: One row per activity (truncated to 1 year)

select *
from {{ ref('fct_strava_activities') }}
where activity_date >= current_date - interval '365 days'
order by activity_date desc, started_at_local desc
