with latest_dates as (
    select
        date,
        name,
        max(date_updated) as latest_date_updated
    from df
    group by date, name
)
select
    df.date,
    df.qty,
    df.name,
    df.units,
    df.date_updated
from df
inner join latest_dates
    on df.date = latest_dates.date
    and df.name = latest_dates.name
    and df.date_updated = latest_dates.latest_date_updated