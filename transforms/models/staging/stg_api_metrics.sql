-- noqa: disable=all
with raw_data as (
    select _raw_data.*
    from {{ source('s3_landing', 'apple_health') }} as _raw_data
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
