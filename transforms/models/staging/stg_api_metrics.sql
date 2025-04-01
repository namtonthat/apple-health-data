with raw_data as (
    select * from
        read_json('s3://{{ var("s3_bucket") }}/landing/health/*.json')
),

unnested_data as (
    select
        raw_data.load_time,
        unnest(data.metrics) as data_metrics
    from raw_data
)

select
    {{ convert_utc_to_melbourne('load_time') }} as load_time,
    struct_extract(data_metrics, 'data') as data_fields,
    struct_extract(data_metrics, 'name') as metric_name,
    struct_extract(data_metrics, 'units') as units
from unnested_data
order by load_time desc
