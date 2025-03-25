"""
Streamlit dashboard for apple-health-data
"""

from datetime import datetime

import conf
import polars as pl
import streamlit as st
from graphing import render_altair_line_chart
from helpers import (
    load_filtered_s3_data,
    sidebar_datetime_filter,
)
from kpi import load_kpi_config, render_kpi_section

# Page configuration
st.set_page_config(
    page_title="🏋️‍♂️Exercise",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏋️ Exercise")

WORKOUT_NAMES = [
    "PL - Deads",
    "PL - Squat",
    "PL - Bench",
    "PL - Accessories",
]


# Sidebar date selection
today = datetime.today().date()
start_date, end_date = sidebar_datetime_filter()

try:
    filtered_exercises = load_filtered_s3_data(
        conf.key_exercises,
        start_date,
        end_date,
    )

    filtered_health = load_filtered_s3_data(
        conf.key_health,
        start_date,
        end_date,
    )

    # Load configuration
    kpi_config = load_kpi_config()


except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()


st.sidebar.header("Exercise Filters")
exercise_type = st.sidebar.multiselect(
    "Workout",
    options=WORKOUT_NAMES,
)


try:
    volumes_by_exercise_df = (
        filtered_exercises.group_by(
            ["metric_date", "workout_name", "exercise_name"],
            maintain_order=True,
        )
        .agg(pl.col("volume").sum())
        .rename({"volume": "quantity"})
    )

    workout_volume_kg = volumes_by_exercise_df.select(["quantity"]).sum().item()

    time_df = (
        filtered_exercises.select(
            ["metric_date", "workout_name", "workout_duration_mins"]
        )
        .unique()
        .rename({"workout_duration_mins": "quantity"})
    )

    workout_time_mins = time_df.select(["quantity"]).sum().item()

    # conversion
    workout_volume_tonnes = workout_volume_kg / 1000
    workout_time_hours = workout_time_mins / 60

    kpi_overrides = {
        "workout_volume_tonnes": workout_volume_tonnes,
        "workout_time_mins": workout_time_mins,
        "workout_time_hours": workout_time_hours,
    }


except Exception as e:
    st.error(f"Error generating base dataframes: {e}")

try:
    render_kpi_section("exercises", filtered_health, kpi_config, kpi_overrides)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Total Volume By Exercise")
        st.write(volumes_by_exercise_df)
        # st.write(filtered_exercises_kpis)
    with col2:
        st.subheader("Workout Details")
        detailed_exercises = filtered_exercises.select(
            [
                "workout_name",
                "metric_date",
                "exercise_name",
                "notes",
                "set_type",
                "weight_kg",
                "reps",
                "rpe",
            ]
            # ).rename(
            #     {"metric_date": "workout_date"},
        )
        st.write(detailed_exercises)

    st.write("Volume and Time Charts")

    col1, col2 = st.columns(2)
    with col1:
        st.bar_chart(
            volumes_by_exercise_df,
            x="metric_date",
            y="volume",
            x_label="Date",
            y_label="Volume (kg)",
            color="exercise_name",
        )
    with col2:
        render_altair_line_chart(time_df, "Time (mins)")

except Exception as e:
    st.error(f"Error computing exercise KPIs: {e}")
