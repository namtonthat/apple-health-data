{{ config(materialized='view') }}

-- Source: Strava activities from raw zone
-- Path: s3://{bucket}/raw/strava/activities/*.parquet

with source as (
    select * from read_parquet('s3://{{ var("s3_bucket") }}/raw/strava/activities/*.parquet', union_by_name = true)
),

staged as (
    select
        -- IDs
        id as activity_id,
        upload_id,
        external_id,

        -- Activity info
        name as activity_name,
        type as activity_type,
        sport_type,
        workout_type,

        -- Timing
        cast(start_date as timestamp) as started_at,
        cast(start_date_local as timestamp) as started_at_local,
        timezone,
        cast(moving_time as integer) as moving_time_seconds,
        cast(elapsed_time as integer) as elapsed_time_seconds,
        round(moving_time / 60.0, 1) as moving_time_minutes,
        round(elapsed_time / 60.0, 1) as elapsed_time_minutes,

        -- Distance & elevation
        round(distance / 1000.0, 2) as distance_km,
        round(distance / 1609.34, 2) as distance_miles,
        round(total_elevation_gain, 1) as elevation_gain_m,
        round(elev_high, 1) as elevation_high_m,
        round(elev_low, 1) as elevation_low_m,

        -- Speed (m/s -> km/h and min/km)
        round(average_speed * 3.6, 2) as avg_speed_kmh,
        round(max_speed * 3.6, 2) as max_speed_kmh,
        case
            when average_speed > 0 then round(1000.0 / average_speed / 60.0, 2)
        end as avg_pace_min_per_km,

        -- Heart rate
        cast(average_heartrate as decimal(5, 1)) as avg_heartrate,
        cast(max_heartrate as integer) as max_heartrate,

        -- Flags
        cast(trainer as boolean) as is_trainer,
        cast(commute as boolean) as is_commute,
        cast(manual as boolean) as is_manual,
        cast(private as boolean) as is_private,
        cast(flagged as boolean) as is_flagged,
        cast(has_heartrate as boolean) as has_heartrate,
        cast(heartrate_opt_out as boolean) as heartrate_opt_out,
        cast(display_hide_heartrate_option as boolean) as hide_heartrate,

        -- Achievements
        cast(achievement_count as integer) as achievement_count,
        cast(kudos_count as integer) as kudos_count,
        cast(comment_count as integer) as comment_count,
        cast(athlete_count as integer) as athlete_count,
        cast(photo_count as integer) as photo_count,
        cast(pr_count as integer) as pr_count,

        -- Metadata
        extracted_at,
        _load_timestamp as load_timestamp,
        _source_file as source_file

    from source
)

select * from staged
