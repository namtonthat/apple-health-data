-- Fail when readiness scores fall outside their documented bounds.

select
    date,
    hrv_score,
    rhr_score,
    sleep_score,
    deep_score,
    readiness_score
from {{ ref('fct_training_readiness') }}
where
    (hrv_score is not null and (hrv_score < 0 or hrv_score > 25))
    or (rhr_score is not null and (rhr_score < 0 or rhr_score > 25))
    or (sleep_score is not null and (sleep_score < 0 or sleep_score > 25))
    or (deep_score is not null and (deep_score < 0 or deep_score > 25))
    or (readiness_score is not null and (readiness_score < 0 or readiness_score > 100))
