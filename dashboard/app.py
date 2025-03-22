"""
Streamlit dashboard for apple-health-data
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import conf
import polars as pl
import streamlit as st
import yaml
from graphing import MACROS_BAR_HEIGHT, render_macros_bar_chart
from helpers import (
    compute_avg_sleep_time_from_midnight,
    convert_column_to_timezone,
    get_average,
    read_parquet_from_s3,
)

# Configure logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------- KPI CONFIG ----------------------
@dataclass
class KPI:
    label: str
    key: str
    format: str = "{}"
    goal: Optional[float] = None
    is_time: bool = False


def load_kpi_config(
    yaml_path: Path = Path(conf.kpi_config_path),
) -> dict[str, list[KPI]]:
    with Path.open(yaml_path) as f:
        raw = yaml.safe_load(f)
    return {section: [KPI(**item) for item in items] for section, items in raw.items()}


def render_kpis(section: str, values: dict[str, Any], config: dict[str, Any]) -> None:
    """
    Render a section of KPI metrics to the Streamlit UI.

    Args:
        section (str): The section name (e.g. "macros", "sleep") to pull config for.
        values (dict[str, Any]): Dictionary of computed KPI values keyed by metric name.
        config (dict[str, Any]): Loaded YAML config mapping sections to KPI definitions.

    This function looks up the metrics for the given section, formats each one according
    to the provided rules (e.g., formatting, delta, time display), and renders them as
    Streamlit metrics.
    """
    kpis = config.get(section, [])
    cols = st.columns(len(kpis))

    for col, kpi in zip(cols, kpis):
        key = kpi.key
        val = values.get(key)
        fmt = kpi.format
        is_time = kpi.is_time

        goal = kpi.goal
        delta = None
        if goal is not None and val is not None and not is_time:
            pct_change = (val - goal) / goal * 100
            delta = f"{pct_change:+.0f}%"

        if is_time and isinstance(val, datetime):
            val_str = val.strftime(fmt)
        elif val is not None:
            val_str = fmt.format(val)
        else:
            val_str = "N/A"

        col.metric(kpi.label, val_str, delta)


# Page configuration
st.set_page_config(
    page_title=conf.page_title,
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title(conf.page_title)


# Sidebar date selection
today = datetime.today().date()
filter_mode = st.sidebar.radio("Filter Mode", ("Quick Filter", "Custom Range"))

if filter_mode == "Quick Filter":
    quick_filter = st.sidebar.radio(
        "Time Range", ["Last Week", "Last Month", "Last 3 Months", "Last 6 Months"]
    )
    delta_map = {
        "Last Week": timedelta(weeks=1),
        "Last Month": timedelta(days=30),
        "Last 3 Months": timedelta(days=90),
        "Last 6 Months": timedelta(days=180),
    }
    start_date = today - delta_map.get(quick_filter, timedelta(weeks=1))
    end_date = today
else:
    start_date = st.sidebar.date_input("Start Date", value=today - timedelta(days=30))
    end_date = st.sidebar.date_input("End Date", value=today)

st.sidebar.write(f"Data from `{start_date}` to `{end_date}`")


@st.cache_data
def load_data_by_key(s3_key: str):
    return read_parquet_from_s3(conf.s3_bucket, s3_key)


def filter_data(df, start_date, end_date):
    """Filter a Polars DataFrame by date and reformat the metric_date column."""
    return df.filter(
        (pl.col("metric_date") >= start_date) & (pl.col("metric_date") <= end_date)
    ).with_columns(pl.col("metric_date").dt.strftime("%Y-%m-%d").alias("metric_date"))


try:
    activity_df = load_data_by_key(conf.key_activity)
    macros_df = load_data_by_key(conf.key_macros)
    sleep_df = load_data_by_key(conf.key_sleep)
    sleep_times_df = load_data_by_key(conf.key_sleep_times)
    # Load configuration
    kpi_config = load_kpi_config()

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Filtering data as per side bar filters
filtered_activity = filter_data(activity_df, start_date, end_date)
filtered_macros = filter_data(macros_df, start_date, end_date)
filtered_sleep = filter_data(sleep_df, start_date, end_date)
filtered_sleep_times = filter_data(sleep_times_df, start_date, end_date)

# ---------------------- AVERAGE activity ----------------------
st.header("Activity")
try:
    avg_activity_df = filtered_activity.group_by("metric_name").agg(
        [pl.col("quantity").mean().alias("avg_quantity")]
    )

    macro_keys = [k.key for k in kpi_config.get("activity", [])]
    activity_values = {key: get_average(avg_activity_df, key) for key in macro_keys}
    render_kpis("activity", activity_values, kpi_config)
except Exception as e:
    st.error(f"Error computing macro KPIs: {e}")

# ---------------------- AVERAGE MACROS ----------------------
st.header("Macros")
try:
    avg_macros_df = filtered_macros.group_by("metric_name").agg(
        [pl.col("quantity").mean().alias("avg_quantity")]
    )

    macro_keys = [k.key for k in kpi_config.get("macros", [])]
    macros_values = {key: get_average(avg_macros_df, key) for key in macro_keys}
    render_kpis("macros", macros_values, kpi_config)
except Exception as e:
    st.error(f"Error computing macro KPIs: {e}")

# Load required macros data
try:
    macros_columns = [
        "carbohydrates",
        "protein",
        "total_fat",
    ]
    _bar_macros = filtered_macros.filter(pl.col("metric_name").is_in(macros_columns))

    bar_macros = _bar_macros.with_columns(
        pl.col("metric_name").replace("total_fat", "fat").alias("metric_name")
    ).sort(pl.col(["metric_date", "metric_name"]))

    calories_df = filtered_macros.filter(pl.col("metric_name") == "calories").sort(
        "metric_date"
    )
    if calories_df.is_empty():
        st.write("No calories data available for the selected date range.")
except Exception as e:
    st.error(f"Error generating data for macros chart: {e}")

# === BAR GRAPH: MACROS BREAKDOWN ===
st.header("Macros Breakdown Bar Chart")
col1, col2 = st.columns(2)
with col1:
    st.bar_chart(
        bar_macros,
        x="metric_date",
        y="quantity",
        color="metric_name",
        x_label="Date",
        y_label="Quantity",
        horizontal=True,
        height=MACROS_BAR_HEIGHT,
    )

with col2:
    # === LINE GRAPH: DAILY CALORIES using st.line_chart ===
    # st.header("Daily Calories Line Chart")
    render_macros_bar_chart(bar_macros)

st.header("Calories")
st.line_chart(
    calories_df.select("metric_date", "quantity"),
    x="metric_date",
    y="quantity",
    x_label="Date",
    y_label="Calories",
    height=400,
)
st.header("Sleep Stats")
try:
    # ---------------------- SLEEP KPIs ----------------------
    sleep_avg_df = filtered_sleep.group_by("metric_name").agg(
        [pl.col("quantity").mean().alias("avg_quantity")]
    )

    # Convert sleep_times to Melbourne timezone
    sleep_times_local = convert_column_to_timezone(filtered_sleep_times, "sleep_times")
    sleep_start_df = sleep_times_local.filter(pl.col("metric_name") == "sleep_start")
    sleep_end_df = sleep_times_local.filter(pl.col("metric_name") == "sleep_end")

    # Compute averages
    avg_sleep_start = compute_avg_sleep_time_from_midnight(sleep_start_df)
    avg_sleep_end = compute_avg_sleep_time_from_midnight(sleep_end_df)

    sleep_keys = [k.key for k in kpi_config.get("sleep", [])]
    sleep_values = {
        key: (
            avg_sleep_start
            if key == "avg_sleep_start"
            else avg_sleep_end
            if key == "avg_sleep_end"
            else get_average(sleep_avg_df, key)
        )
        for key in sleep_keys
    }

    render_kpis("sleep", sleep_values, kpi_config)
except Exception as e:
    st.error(f"Error computing sleep KPIs: {e}")
