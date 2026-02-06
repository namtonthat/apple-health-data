{{ config(materialized='view') }}

-- Source: Cleansed Apple Health metrics from raw zone
-- Path: s3://{bucket}/raw/health/health_metrics/*.parquet

with source as (
    select * from read_parquet('s3://{{ var("s3_bucket") }}/raw/health/health_metrics/*.parquet')
),

staged as (
    select
        -- Primary key
        _dlt_id as metric_id,

        -- Dimensions
        metric_date::date as metric_date,
        metric_name,
        units,
        source as data_source,

        -- Main value
        value,

        -- Sleep breakdown (only for sleep_analysis metric)
        rem as sleep_rem_hours,
        deep as sleep_deep_hours,
        core as sleep_core_hours,
        awake as sleep_awake_hours,

        -- Cleanse metadata
        file_timestamp as export_timestamp,
        _load_timestamp,
        _source_file,
        _source_system

    from source
),

-- Deduplicate: keep one record per date/metric/source combination
deduplicated as (
    select
        *,
        row_number() over (
            partition by metric_date, metric_name, data_source
            order by export_timestamp desc
        ) as row_num
    from staged
)

select
    metric_id,
    metric_date,
    metric_name,
    units,
    data_source,
    value,
    sleep_rem_hours,
    sleep_deep_hours,
    sleep_core_hours,
    sleep_awake_hours,
    export_timestamp,
    _load_timestamp,
    _source_file,
    _source_system
from deduplicated
where row_num = 1
