import logging
from datetime import datetime, timedelta

import conf
import polars as pl
import streamlit as st
from helpers import (
    read_parquet_from_s3,
)

# Configure logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.title("Nam Tonthat's Health Data")

# === SIDEBAR DATE FILTER ===
st.sidebar.header("Date Filter")
filter_mode = st.sidebar.radio(
    "Select Date Filter Mode", ("Quick Filter", "Custom Range")
)
today = datetime.today().date()

if filter_mode == "Quick Filter":
    quick_filter = st.sidebar.selectbox(
        "Select Time Range",
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

st.sidebar.write(f"Filtering data from {start_date} to {end_date}")

# === LOAD AND FILTER SLEEP DATA ===
try:
    sleep_df = read_parquet_from_s3(conf.s3_bucket, conf.key_sleep)

    filtered_sleep = sleep_df.filter(
        (pl.col("metric_date") >= start_date) & (pl.col("metric_date") <= end_date)
    ).with_columns(pl.col("metric_date").dt.strftime("%Y-%m-%d").alias("metric_date"))
    # st.header("Sleep Data")
    # st.dataframe(filtered_sleep)
except Exception as e:
    st.error(f"Error loading sleep data: {e}")

# === LOAD AND FILTER MACROS DATA ===
try:
    macros_df = read_parquet_from_s3(conf.s3_bucket, conf.key_macros)
    filtered_macros = macros_df.filter(
        (pl.col("metric_date") >= start_date) & (pl.col("metric_date") <= end_date)
    ).with_columns(pl.col("metric_date").dt.strftime("%Y-%m-%d").alias("metric_date"))
    # st.header("Macros Data")
    # st.dataframe(filtered_macros)
except Exception as e:
    st.error(f"Error loading macros data: {e}")

st.header("Average Macros KPIs")
try:
    # Calculate average macros using Polars group_by
    avg_macros = filtered_macros.group_by("metric_name").agg(
        [pl.col("quantity").mean().alias("avg_quantity")]
    )

    def get_avg(metric: str):
        """Helper function to extract average value for a given metric."""
        df_metric = avg_macros.filter(pl.col("metric_name") == metric)
        return df_metric["avg_quantity"][0] if df_metric.height > 0 else None

    # Mapping of display labels to the corresponding metric keys
    metrics = {
        "Carbohydrates (g)": "carbohydrates",
        "Protein (g)": "protein",
        "Fat (g)": "total_fat",
        "Fibre (g)": "fiber",
        "Calories (kcal)": "calories",
    }

    # Calculate averages in one step
    avg_values = {label: get_avg(key) for label, key in metrics.items()}

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
        # "fiber",
        "protein",
        "total_fat",
    ]
    bar_macros = filtered_macros.filter(
        pl.col("metric_name").is_in(macros_columns)
    ).sort(pl.col(["metric_date", "metric_name"]))

    bar_chart_data = bar_macros.group_by("metric_name").agg(
        [pl.col("quantity").mean().alias("avg_quantity")]
    )

    pivot_df = bar_macros.pivot(
        index="metric_date",
        columns="metric_name",
        values="quantity",
        aggregate_function="mean",
    )
    st.dataframe(pivot_df)
    st.dataframe(bar_macros)

    st.bar_chart(bar_macros, x="metric_date", y="quantity", color="metric_name")
except Exception as e:
    st.error(f"Error generating bar chart: {e}")

# === LINE GRAPH: DAILY CALORIES using st.line_chart ===
st.header("Daily Calories Line Chart")
try:
    calories_df = filtered_macros.filter(pl.col("metric_name") == "calories").sort(
        "metric_date"
    )
    if not calories_df.empty:
        # Assuming 'quantity' represents daily calories.
        st.line_chart(calories_df[["quantity"]])
    else:
        st.write("No calories data available for the selected date range.")
except Exception as e:
    st.error(f"Error generating line chart for calories: {e}")

st.header("Sleep Stats KPIs")
try:
    # --- Compute averages from sleep data ---
    avg_sleep_asleep = filtered_sleep.filter(pl.col("metric_name") == "asleep")
    st.write(avg_sleep_asleep)

    avg_sleep = filtered_sleep.group_by("metric_name").agg(
        [pl.col("quantity").mean().alias("avg_quantity")]
    )

    def get_sleep_avg(metric: str):
        df_metric = avg_sleep.filter(pl.col("metric_name") == metric)
        return df_metric["avg_quantity"][0] if df_metric.height > 0 else None

    avg_asleep = get_sleep_avg("asleep")
    avg_deep_sleep = get_sleep_avg("deep_sleep")
    avg_in_bed = get_sleep_avg("in_bed")

    # Calculate sleep efficiency (asleep/in_bed * 100)
    efficiency = (
        (avg_asleep / avg_in_bed * 100)
        if avg_asleep is not None and avg_in_bed not in (None, 0)
        else None
    )

    # Compute delta vs goals for asleep and deep_sleep
    delta_asleep = (avg_asleep - 7) if avg_asleep is not None else None
    delta_deep_sleep = (avg_deep_sleep - 2) if avg_deep_sleep is not None else None

    in_bed_time = filtered_sleep.filter(pl.col("metric_name") == "in_bed_time")
    st.write(in_bed_time)
    # if not in_bed_time.empty:
    # Convert the in_bed_times column to datetime (if not already)
    # in_bed_time["in_bed_time"] = pd.to_datetime(in_bed_time["in_bed_times"])
    # avg_in_bed_time = in_bed_time["in_bed_time"].mean()
    # avg_in_bed_time_formatted = avg_in_bed_time.strftime("%I:%M %p")
    # # Set goal: 11:00 PM on the same day as the average (date doesn't matter)
    # goal_in_bed_time = avg_in_bed_time.replace(
    #     hour=23, minute=0, second=0, microsecond=0
    # )
    # # Calculate delta in minutes (positive means later than goal, negative means earlier)
    # delta_minutes = (avg_in_bed_time - goal_in_bed_time).total_seconds() / 60
    # else:
    #     avg_in_bed_time_formatted = "N/A"
    #     delta_minutes = None

    # --- Display Sleep KPIs ---
    # Display Asleep, Deep Sleep, and Sleep Start (average bedtime)
    # col1, col2, col3, col4 = st.columns(4)
    # with col1:
    #     st.metric(
    #         "Time Asleep (h)",
    #         f"{avg_asleep:.1f}" if avg_asleep is not None else "N/A",
    #         delta=f"{delta_asleep:+.1f}h" if delta_asleep is not None else "",
    #     )
    # with col2:
    #     st.metric(
    #         "Deep Sleep (h)",
    #         f"{avg_deep_sleep:.1f}" if avg_deep_sleep is not None else "N/A",
    #         delta=f"{delta_deep_sleep:+.1f}h" if delta_deep_sleep is not None else "",
    #     )
    # with col3:
    #     st.metric(
    #         "Sleep Start",
    #         avg_in_bed_time_formatted,
    #         delta=f"{delta_minutes:+.0f}m" if delta_minutes is not None else "",
    #     )
    # # Optionally, display Sleep Efficiency in a separate metric.
    # with col4:
    #     st.metric(
    #         "Sleep Efficiency",
    #         f"{efficiency:.0f}%" if efficiency is not None else "N/A",
    #     )

except Exception as e:
    st.error(f"Error computing sleep KPIs: {e}")

# # === REFLECTION FORM ===
# st.header("Weekly Reflection")
# with st.form("reflection_form"):
#     q1 = st.text_input("How was your mood?")
#     q2 = st.text_input("Energy level?")
#     q3 = st.text_input("Stress level?")
#     q4 = st.text_input("Productivity?")
#     q5 = st.text_input("Overall feeling?")
#     submit = st.form_submit_button("Submit Reflection")
#
# if submit:
#     new_entry = {
#         "week": datetime.now().strftime("%Y-%W"),
#         "q1": q1,
#         "q2": q2,
#         "q3": q3,
#         "q4": q4,
#         "q5": q5,
#         "timestamp": datetime.now().isoformat(),
#     }
#     try:
#         insert_reflections_into_duckdb(conf.duckdb_path, new_entry)
#         st.success("Reflection submitted!")
#     except Exception as e:
#         st.error(f"Error submitting reflection: {e}")
#
# # === DISPLAY REFLECTION DATA ===
# st.header("Reflection Data")
# try:
#     reflections_df = load_reflections_from_duckdb(conf.duckdb_path)
#     st.dataframe(reflections_df)
# except Exception as e:
#     st.error(f"Error loading reflections: {e}")
