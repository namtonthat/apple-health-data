with latest_load_date as (
    select max(ctrl_load_date) as max_ctrl_load_date
    from {{ ref('stg_openpowerlifting') }}
)

select
    opl.name,
    opl.sex,
    opl.event,
    opl.equipment,
    opl.age,
    opl.age_class,
    opl.birth_year_class,
    opl.division,
    opl.bodyweight_kg,
    opl.weight_class_kg,
    opl.squat1_kg,
    opl.squat2_kg,
    opl.squat3_kg,
    opl.squat4_kg,
    opl.best3_squat_kg,
    opl.bench1_kg,
    opl.bench2_kg,
    opl.bench3_kg,
    opl.bench4_kg,
    opl.best3_bench_kg,
    opl.deadlift1_kg,
    opl.deadlift2_kg,
    opl.deadlift3_kg,
    opl.deadlift4_kg,
    opl.best3_deadlift_kg,
    opl.total_kg,
    opl.place,
    opl.dots,
    opl.wilks,
    opl.glossbrenner,
    opl.goodlift,
    opl.tested,
    opl.country,
    opl.state,
    opl.federation,
    opl.parent_federation,
    opl.metric_date,
    opl.meet_country,
    opl.meet_state,
    opl.meet_town,
    opl.meet_name,
    opl.sanctioned,
    opl.ctrl_load_date
from {{ ref('stg_openpowerlifting') }} as opl
inner join
    latest_load_date
    on opl.ctrl_load_date = latest_load_date.max_ctrl_load_date
