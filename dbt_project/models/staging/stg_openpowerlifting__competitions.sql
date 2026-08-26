{{ config(materialized='view') }}

-- Source: OpenPowerlifting competition results (lifter CSV API, landed by dlt)
-- Path: s3://{bucket}/landing_openpowerlifting/competitions/*.parquet

with source as (
    select *
    from read_parquet('s3://{{ var("s3_bucket") }}/landing_openpowerlifting/competitions/*.parquet')
),

staged as (
    select
        -- Athlete info
        name as athlete_name,
        sex,
        country,

        -- Competition info
        meet_name as competition_name,
        date::date as competition_date,
        meet_country,
        meet_state,
        federation,

        -- Division & weight
        division,
        try_cast(bodyweight_kg as double) as bodyweight_kg,
        weight_class_kg,
        age,

        -- Lifts (best attempts)
        try_cast(best3_squat_kg as double) as squat_kg,
        try_cast(best3_bench_kg as double) as bench_kg,
        try_cast(best3_deadlift_kg as double) as deadlift_kg,
        try_cast(total_kg as double) as total_kg,

        -- Scoring
        try_cast(dots as double) as dots_score,
        try_cast(wilks as double) as wilks_score,
        place,

        -- Equipment
        equipment,
        tested as drug_tested

    from source
)

select * from staged
