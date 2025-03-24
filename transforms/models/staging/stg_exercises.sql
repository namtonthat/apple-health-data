with raw_data as (
    select * from
        read_json('s3://{{ var("s3_bucket") }}/landing/exercise/*.json')
)
-- casted_raw_data as (
--     select
--         id,
--         title,
--         start_time,
--         end_time,
--         updated_at,
--         created_at,
--         cast(ctrl_load_date as datetime) as ctrl_load_date,
--         exercises
--     from raw_data 
--   ),
-- latest_dates as (
--     select 
--         id,
--         max(cast(ctrl_load_date as datetime)) as latest_ctrl_load_date
--     from raw_data
--     group by id
-- )
--     select
--         rd.id,
--         rd.title,
--         rd.start_time,
--         rd.end_time,
--         rd.updated_at,
--         rd.created_at,
--         rd.ctrl_load_date,
--         unnest(rd.exercises, recursive := true)
--     from casted_raw_data rd
-- inner join latest_dates ld
--     on rd.id = ld.id
--    and rd.ctrl_load_date = ld.latest_ctrl_load_date
select * from raw_data
