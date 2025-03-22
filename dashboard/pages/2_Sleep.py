"""
Streamlit dashboard for apple-health-data
"""

import logging
from datetime import datetime

import conf
import polars as pl
import streamlit as st
from graphing import (
    filter_metrics,
)
from helpers import (
    compute_avg_sleep_time_from_midnight,
    convert_column_to_timezone,
    load_data_by_key,
    sidebar_date_filter,
)
from kpi import load_kpi_config, render_kpi_section

# Configure logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(
    page_title="Mental State",
    page_icon="🌒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌒 Mental State")


# Sidebar date selection
today = datetime.today().date()
start_date, end_date = sidebar_date_filter()


try:
    filtered_activity = load_data_by_key(conf.key_activity, start_date, end_date)
    filtered_sleep = load_data_by_key(conf.key_sleep, start_date, end_date)
    filtered_sleep_times = load_data_by_key(conf.key_sleep_times, start_date, end_date)
    # Load configuration
    kpi_config = load_kpi_config()

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Filtering data as per side bar filters

# ---------------------- AVERAGE activity ----------------------
st.header("Activity")
try:
    render_kpi_section("activity", filtered_activity, kpi_config)
except Exception as e:
    st.error(f"Error computing macro KPIs: {e}")


st.header("Sleep Stats")
try:
    # ---------------------- SLEEP KPIs ----------------------
    sleep_avg_df = filtered_sleep.group_by("metric_name").agg(
        [pl.col("quantity").mean().alias("avg_quantity")]
    )

    # Convert sleep_times to Melbourne timezone
    sleep_times_local = convert_column_to_timezone(filtered_sleep_times, "sleep_times")
    sleep_start_df = filter_metrics(sleep_times_local, ["sleep_start"])
    sleep_end_df = filter_metrics(sleep_times_local, ["sleep_end"])

    # Compute averages
    avg_sleep_start = compute_avg_sleep_time_from_midnight(sleep_start_df)
    avg_sleep_end = compute_avg_sleep_time_from_midnight(sleep_end_df)

    sleep_overrides = {
        "avg_sleep_start": avg_sleep_start,
        "avg_sleep_end": avg_sleep_end,
    }
    #
    render_kpi_section("sleep", filtered_sleep, kpi_config, overrides=sleep_overrides)
except Exception as e:
    st.error(f"Error computing sleep KPIs: {e}")
