"""
Streamlit dashboard for apple-health-data
"""

from datetime import datetime

import conf
import polars as pl
import streamlit as st
from graphing import filter_metrics, render_altair_line_chart
from helpers import (
    compute_avg_sleep_time,
    convert_column_to_timezone,
    load_filtered_s3_data,
    sidebar_datetime_filter,
)
from kpi import load_kpi_config, render_kpi_section

# Page configuration
st.set_page_config(
    page_title="Mental Health",
    page_icon="🌒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌒 Mental Health")


# Sidebar date selection
today = datetime.today().date()
start_date, end_date = sidebar_datetime_filter()


def format_hours_to_duration_str(
    column_name: str, label: str = "Formatted Duration"
) -> pl.Expr:
    col = pl.col(column_name)
    hours = col.floor().cast(pl.Int64).cast(pl.Utf8)
    minutes = ((col - col.floor()) * 60).round(0).cast(pl.Int64).cast(pl.Utf8)

    return (hours + "h " + minutes + "m").alias(label)


try:
    filtered_health = load_filtered_s3_data(conf.key_health, start_date, end_date)
    filtered_sleep_times = load_filtered_s3_data(
        conf.key_sleep_times,
        start_date,
        end_date,
    )
    filtered_sleep = load_filtered_s3_data(
        conf.key_sleep,
        start_date,
        end_date,
    )

    # Load configuration
    kpi_config = load_kpi_config()

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# ---------------------- AVERAGE activity ----------------------
st.header("Activity")
try:
    render_kpi_section("activity", filtered_health, kpi_config)
except Exception as e:
    st.error(f"Error computing macro KPIs: {e}")


st.header("Sleep Stats")
try:
    # ---------------------- SLEEP KPIs ----------------------
    # Convert sleep_times to Melbourne timezone
    sleep_times_local = convert_column_to_timezone(
        filtered_sleep_times, "sleep_times"
    ).sort("sleep_times", descending=[False])
    sleep_start_df = filter_metrics(sleep_times_local, ["sleep_start"])
    sleep_end_df = filter_metrics(sleep_times_local, ["sleep_end"])

    # Compute averages
    avg_sleep_start = compute_avg_sleep_time(sleep_start_df)
    avg_sleep_end = compute_avg_sleep_time(sleep_end_df)

    sleep_overrides = {
        "avg_sleep_start": avg_sleep_start,
        "avg_sleep_end": avg_sleep_end,
    }

    render_kpi_section("sleep", filtered_health, kpi_config, overrides=sleep_overrides)

    col1, col2 = st.columns(2)
    asleep = filtered_sleep.filter(pl.col("metric_name") == "asleep").with_columns(
        format_hours_to_duration_str("quantity", label="Sleep Duration")
    )

    sleep_time_details = (
        sleep_times_local.select(pl.col(["metric_date", "sleep_times", "metric_name"]))
        .pivot("metric_name", index="metric_date", values="sleep_times")
        .rename(
            {
                "metric_date": "Date",
                "sleep_start": "Start",
                "sleep_end": "End",
            }
        )
        .with_columns(
            # Format Sleep Start and Sleep End as strings for display
            pl.col("Start").dt.strftime("%I:%M %p"),
            pl.col("End").dt.strftime("%I:%M %p"),
        )
    ).join(
        asleep.select(["metric_date", "Sleep Duration"]).rename(
            {"metric_date": "Date"}
        ),
        on="Date",
    )

    with col1:
        st.subheader("Detail")
        st.write(sleep_time_details)

    with col2:
        st.subheader("Sleep Over Time")
        render_altair_line_chart(
            asleep,
            title="Sleep Hours (hrs)",
            avg_bar=7,
        )
except Exception as e:
    st.error(f"Error computing sleep KPIs: {e}")
