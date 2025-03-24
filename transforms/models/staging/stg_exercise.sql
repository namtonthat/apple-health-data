with raw_data as (
    select * from
        read_json('s3://{{ var("s3_bucket") }}/landing/exercise/*.json')
),

unnested_data as (
    select
        id,
        title,
        start_time,
        end_time,
        updated_at,
        created_at,
        unnest(exercises, recursive := true) 
    from raw_data
)

select
    id,
    title,
    start_time,
    end_time,
    updated_at,
    created_at,
    unnest(sets).type as set_type,
    unnest(sets).weight_kg as weight_kg,
    unnest(sets).reps as reps,
    unnest(sets).rpe as rpe
from unnested_data
