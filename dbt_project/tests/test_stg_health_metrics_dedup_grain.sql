-- Fail when the (metric_date, metric_name, data_source) dedup key --
-- the row_number() partition in stg_health__metrics -- is not unique.
-- metric_id (dlt row id) is trivially unique regardless of dedup
-- correctness, so this composite check is what actually catches a
-- broken partition/order-by in the staging dedup logic.

select
    metric_date,
    metric_name,
    data_source,
    count(*) as row_count
from {{ ref('stg_health__metrics') }}
group by metric_date, metric_name, data_source
having count(*) > 1
