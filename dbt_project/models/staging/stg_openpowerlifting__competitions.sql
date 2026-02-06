{{ config(materialized='view') }}

-- Source: OpenPowerlifting competition results
-- Path: s3://{bucket}/raw/openpowerlifting.parquet

with source as (
    select * from read_parquet('s3://{{ var("s3_bucket") }}/raw/openpowerlifting.parquet')
),

staged as (
    select
        -- Athlete info
        Name as athlete_name,
        Sex as sex,
        Country as country,

        -- Competition info
        meet_name as competition_name,
        metric_date::date as competition_date,
        meet_country,
        meet_state,
        Federation as federation,

        -- Division & weight
        Division as division,
        bodyweight_kg,
        weight_class_kg,
        Age as age,

        -- Lifts (best attempts)
        best3_squat_kg as squat_kg,
        best3_bench_kg as bench_kg,
        best3_deadlift_kg as deadlift_kg,
        total_kg,

        -- Scoring
        Dots as dots_score,
        Wilks as wilks_score,
        Place as place,

        -- Equipment
        Equipment as equipment,
        Tested as drug_tested

    from source
)

select * from staged
order by competition_date desc
