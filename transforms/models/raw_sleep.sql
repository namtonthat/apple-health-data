select * from {{ ref('stg_api_metrics') }}
where metric_name = 'sleep_analysis'
