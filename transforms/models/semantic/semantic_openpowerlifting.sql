select
    metric_date,
    metric_name,
    quantity,
    units
from {{ ref('raw_openpowerlifting') }}
