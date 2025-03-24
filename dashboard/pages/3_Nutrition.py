"""
Streamlit dashboard for apple-health-data
"""

import conf
import streamlit as st
from graphing import (
    MACROS_BAR_HEIGHT,
    filter_metrics,
    render_macros_bar_chart,
)
from helpers import (
    load_data_by_key,
    sidebar_date_filter,
)
from kpi import load_kpi_config, render_kpi_section

# Page configuration
st.set_page_config(
    page_title="Nutrition",
    page_icon="🥄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🧑‍🍳 Nutrition")

start_date, end_date = sidebar_date_filter()


try:
    filtered_df = load_data_by_key(conf.key_nutrition, start_date, end_date)
    # Load configuration
    kpi_config = load_kpi_config()

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()


try:
    render_kpi_section("nutrition", filtered_df, kpi_config)
except Exception as e:
    st.error(f"Error computing macro KPIs: {e}")

# Load required macros data
try:
    macros_df = filter_metrics(
        df=filtered_df,
        metrics=["carbohydrates", "protein", "total_fat"],
        rename_map={"total_fat": "fat"},
    )
    calories_df = filter_metrics(filtered_df, metrics=["calories"])

except Exception as e:
    st.error(f"Error generating data for macros chart: {e}")

# === BAR GRAPH: MACROS BREAKDOWN ===
st.header("Breakdown Bar Chart")
col1, col2 = st.columns(2)
with col1:
    st.bar_chart(
        macros_df,
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
    render_macros_bar_chart(macros_df)

st.header("Calories")
st.line_chart(
    calories_df.select("metric_date", "quantity"),
    x="metric_date",
    y="quantity",
    x_label="Date",
    y_label="Calories",
    height=400,
)
