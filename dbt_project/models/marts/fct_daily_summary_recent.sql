{{
  config(
    materialized='external',
    location='s3://{{ var("s3_bucket") }}/transformed/fct_daily_summary_recent'
  )
}}

-- Last 90 days of daily summary for fast dashboard reads
-- Grain: One row per calendar day (truncated to 90 days)

select *
from {{ ref('fct_daily_summary') }}
where date >= current_date - interval '90 days'
order by date desc
