"""
Streamlit dashboard for apple-health-data
"""

import conf
import polars as pl
import streamlit as st
from graphing import (
    filter_metrics,
    render_altair_line_chart,
    render_macros_bar_chart,
)
from helpers import (
    load_filtered_s3_data,
    sidebar_datetime_filter,
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

start_date, end_date = sidebar_datetime_filter()


try:
    filtered_df = load_filtered_s3_data(conf.key_health, start_date, end_date)
    # Load configuration
    kpi_config = load_kpi_config()

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Load required macros data
try:
    macros_and_calories_df = filter_metrics(
        df=filtered_df,
        metrics=[
            "carbohydrates",
            "protein",
            "total_fat",
            "calories",
            "calories_carbohydrates",
            "calories_fat",
            "calories_protein",
        ],
        rename_map={"total_fat": "fat"},
    ).with_columns(pl.col("quantity").round(0))

    macros_df = filter_metrics(
        df=macros_and_calories_df, metrics=["carbohydrates", "protein", "fat"]
    )
    calories_by_macros_df = filter_metrics(
        df=macros_and_calories_df,
        metrics=["calories_carbohydrates", "calories_protein", "calories_fat"],
    )
    calories_df = filter_metrics(macros_and_calories_df, metrics=["calories"])
    weight_df = filter_metrics(filtered_df, metrics=["weight_body_mass"])

except Exception as e:
    st.error(f"Error generating data for macros chart: {e}")

try:
    render_kpi_section("nutrition", filtered_df, kpi_config)
except Exception as e:
    st.error(f"Error computing macro KPIs: {e}")


st.header("Weight and Calories")
col1, col2 = st.columns(2)
with col1:
    render_altair_line_chart(calories_df, "Calories")

with col2:
    render_altair_line_chart(weight_df, "Weight")

# === BAR GRAPH: MACROS BREAKDOWN ===
st.header("Breakdown Bar Chart")
col1, col2 = st.columns(2)
with col1:
    st.bar_chart(
        calories_by_macros_df,
        x="metric_date",
        y="quantity",
        color="metric_name",
        x_label="Calories (kcal)",
        y_label="Date",
        horizontal=True,
        height=500,
    )

with col2:
    # === LINE GRAPH: DAILY CALORIES using st.line_chart ===
    render_macros_bar_chart(macros_df)

st.header("Detailed Macros")
detailed_macros_df = (
    macros_and_calories_df.filter(
        pl.col("metric_name").is_in(["carbohydrates", "fat", "protein", "calories"])
    )
    .pivot("metric_name", index="metric_date", values="quantity")
    .sort("metric_date", descending=False)
    .rename({"metric_date": "date"})
)

st.write(detailed_macros_df)
