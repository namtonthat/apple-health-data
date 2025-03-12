{{
    config(
        post_hook=[
            "COPY {{ this }} TO 's3://{{ var('s3_bucket') }}/raw/raw_api_metrics.parquet'"
        ]
    )
}}

with raw_api_metrics as (
    select
        cast(unnest(data_fields).date as date) as metric_date,
        metric_name,
        units,
        round(unnest(data_fields).qty, 2) as quantity
    from {{ ref('stg_api_metrics') }}
)

select *
from raw_api_metrics
order by metric_date asc, metric_name asc
