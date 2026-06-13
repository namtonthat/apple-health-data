-- Source contract: fail when a critical Apple Health metric_name is absent from
-- staging. The daily pivots match metric_name string-literally, so if an export
-- renames one of these the corresponding column silently goes all-null. This test
-- makes that break loudly instead.

with expected (metric_name) as (
    values
    ('step_count'),
    ('active_energy'),
    ('basal_energy_burned'),
    ('walking_running_distance'),
    ('resting_heart_rate'),
    ('heart_rate_variability'),
    ('vo2_max'),
    ('sleep_analysis'),
    ('weight_body_mass'),
    ('protein'),
    ('carbohydrates'),
    ('total_fat'),
    ('dietary_energy')
),

present as (
    select distinct metric_name
    from {{ ref('stg_health__metrics') }}
)

select e.metric_name
from expected e
left join present p on e.metric_name = p.metric_name
where p.metric_name is null
