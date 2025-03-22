"""
Streamlit dashboard for apple-health-data
"""

import logging
from datetime import datetime, timedelta

import conf
import polars as pl
import streamlit as st
from helpers import (
    get_average,
    read_parquet_from_s3,
)

# Configure logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Variables
PAGE_TITLE = "Nam Tonthat's Health Data"
SLEEP_GOAL = 7
DEEP_SLEEP_GOAL = 2

# Page configuration
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title(PAGE_TITLE)

# === SIDEBAR DATE FILTER ===
st.sidebar.header("Date Filter")
filter_mode = st.sidebar.radio("Filter Mode", ("Quick Filter", "Custom Range"))
today = datetime.today().date()

if filter_mode == "Quick Filter":
    quick_filter = st.sidebar.radio(
        "Time Range",
        ["Last Week", "Last Month", "Last 3 Months", "Last 6 Months"],
    )
    if quick_filter == "Last Month":
        start_date = today - timedelta(days=30)
    elif quick_filter == "Last 3 Months":
        start_date = today - timedelta(days=90)
    elif quick_filter == "Last 6 Months":
        start_date = today - timedelta(days=180)
    else:
        # Default to last week
        start_date = today - timedelta(weeks=1)
    end_date = today

else:
    start_date = st.sidebar.date_input("Start Date", value=today - timedelta(days=30))
    end_date = st.sidebar.date_input("End Date", value=today)

st.sidebar.write(f"Data from `{start_date}` to `{end_date}`")


@st.cache_data
def load_data():
    sleep_df = read_parquet_from_s3(conf.s3_bucket, conf.key_sleep)
    macros_df = read_parquet_from_s3(conf.s3_bucket, conf.key_macros)
    return sleep_df, macros_df


def filter_data(df, start_date, end_date):
    """Filter a Polars DataFrame by date and reformat the metric_date column."""
    return df.filter(
        (pl.col("metric_date") >= start_date) & (pl.col("metric_date") <= end_date)
    ).with_columns(pl.col("metric_date").dt.strftime("%Y-%m-%d").alias("metric_date"))


try:
    sleep_df, macros_df = load_data()
    filtered_sleep = filter_data(sleep_df, start_date, end_date)
    filtered_macros = filter_data(macros_df, start_date, end_date)
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

st.header("Average Macros")
try:
    # Calculate average macros using Polars group_by
    avg_macros = filtered_macros.group_by("metric_name").agg(
        [pl.col("quantity").mean().alias("avg_quantity")]
    )
    # Mapping of display labels to the corresponding metric keys
    metrics = {
        "Calories (kcal)": "calories",
        "Carbohydrates (g)": "carbohydrates",
        "Protein (g)": "protein",
        "Fat (g)": "total_fat",
        "Fibre (g)": "fiber",
    }

    # Calculate averages in one step
    avg_values = {label: get_average(avg_macros, key) for label, key in metrics.items()}

    # Create columns dynamically based on the number of metrics
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, avg_values.items()):
        col.metric(label, f"{value:.0f}" if value is not None else "N/A")

except Exception as e:
    st.error(f"Error computing macro KPIs: {e}")

# === BAR GRAPH: MACROS BREAKDOWN (EXCLUDING CALORIES) ===
st.header("Macros Breakdown Bar Chart")
try:
    macros_columns = [
        "carbohydrates",
        "protein",
        "total_fat",
    ]
    bar_macros = filtered_macros.filter(
        pl.col("metric_name").is_in(macros_columns)
    ).sort(pl.col(["metric_date", "metric_name"]))

    bar_chart_data = bar_macros.group_by("metric_name").agg(
        [pl.col("quantity").mean().alias("avg_quantity")]
    )

    # st.dataframe(bar_macros)

    st.bar_chart(bar_macros, x="metric_date", y="quantity", color="metric_name")
except Exception as e:
    st.error(f"Error generating bar chart: {e}")

# === LINE GRAPH: DAILY CALORIES using st.line_chart ===
# st.header("Daily Calories Line Chart")
try:
    calories_df = filtered_macros.filter(pl.col("metric_name") == "calories").sort(
        "metric_date"
    )
    # st.write(calories_df)
    if calories_df.is_empty():
        st.write("No calories data available for the selected date range.")
    else:
        st.line_chart(
            calories_df.select("metric_date", "quantity"), x="metric_date", y="quantity"
        )

except Exception as e:
    st.error(f"Error generating line chart: {e}")

st.header("Sleep Stats")
try:
    # Compute average sleep metrics.
    avg_sleep = filtered_sleep.group_by("metric_name").agg(
        [pl.col("quantity").mean().alias("avg_quantity")]
    )

    # Extract sleep metrics (assume these values exist because the data loaded successfully)
    avg_asleep = get_average(avg_sleep, "asleep")
    avg_deep = get_average(avg_sleep, "deep_sleep")
    avg_in_bed = get_average(avg_sleep, "in_bed")

    # Calculate sleep efficiency and deltas against goals.
    efficiency = avg_asleep / avg_in_bed * 100
    delta_asleep = avg_asleep - SLEEP_GOAL  # Goal: 7 hours asleep
    delta_deep = avg_deep - DEEP_SLEEP_GOAL  # Goal: 2 hours deep sleep

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Time Asleep (h)", f"{avg_asleep:.1f}", delta=f"{delta_asleep:+.1f}h")
    with col2:
        st.metric("Deep Sleep (h)", f"{avg_deep:.1f}", delta=f"{delta_deep:+.1f}h")
    with col3:
        st.metric("Time in Bed (h)", f"{avg_in_bed:.1f}")
    with col4:
        st.metric("Sleep Efficiency", f"{efficiency:.0f}%")
except Exception as e:
    st.error(f"Error computing sleep KPIs: {e}")
