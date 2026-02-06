{{
    config(
        materialized='external',
        location="s3://{{ var('s3_bucket') }}/transformed/fct_strava_activities",
        format='parquet'
    )
}}

with activities as (
    select * from {{ ref('stg_strava__activities') }}
),

final as (
    select
        -- IDs
        activity_id,

        -- Activity info
        activity_name,
        activity_type,
        sport_type,

        -- Date/time
        cast(started_at_local as date) as activity_date,
        started_at_local,
        timezone,
        moving_time_minutes,
        elapsed_time_minutes,

        -- Distance & elevation
        distance_km,
        distance_miles,
        elevation_gain_m,

        -- Speed & pace
        avg_speed_kmh,
        max_speed_kmh,
        avg_pace_min_per_km,

        -- Heart rate
        avg_heartrate,
        max_heartrate,

        -- Flags
        is_trainer,
        is_commute,

        -- Achievements
        achievement_count,
        pr_count,

        -- Metadata
        extracted_at

    from activities
    where activity_type is not null
)

select * from final
order by activity_date desc, started_at_local desc
