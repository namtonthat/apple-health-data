with raw_data as (
    select * from
        read_json('s3://{{ var("s3_bucket") }}/landing/*.json')
),

unnested_data as (
    select
        raw_data.load_date,
        unnest(data.metrics) as data_metrics
    from raw_data

)

select
    load_date,
    struct_extract(data_metrics, 'data') as data_fields,
    struct_extract(data_metrics, 'name') as metric_name,
    struct_extract(data_metrics, 'units') as units
from unnested_data
