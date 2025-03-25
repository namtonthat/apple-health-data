"""
Streamlit dashboard for apple-health-data
"""

from datetime import datetime

import conf
import polars as pl
import streamlit as st
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


# Sidebar date selection
today = datetime.today().date()
start_date, end_date = sidebar_datetime_filter()


try:
    filtered_exercises = load_filtered_s3_data(
        conf.key_exercises,
        start_date,
        end_date,
    )

    filtered_exercises_kpis = load_filtered_s3_data(
        conf.key_exercises_kpis,
        start_date,
        end_date,
    )

    # Load configuration
    kpi_config = load_kpi_config()

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

try:
    volumes_by_exercise_df = filtered_exercises.group_by(
        ["metric_date", "workout_name", "exercise_name"],
        maintain_order=True,
    ).agg(pl.col("volume").sum())
    st.write(volumes_by_exercise_df)
    volume_df = filtered_exercises_kpis.filter(
        pl.col("metric_name") == "workout_volume"
    )
    time_df = filtered_exercises_kpis.filter(pl.col("metric_name") == "workout_time")

    sum_workout_volume_kg = volume_df.select(pl.col("quantity").sum()).item()
    sum_workout_time_mins = time_df.select(pl.col("quantity").sum()).item()

    # conversion
    sum_workout_volume_tonnes = sum_workout_volume_kg / 1000
    sum_workout_time_hours = sum_workout_time_mins / 60

    kpi_overrides = {
        "workout_volume_tonnes": sum_workout_volume_tonnes,
        "workout_time_mins": sum_workout_time_mins,
        "workout_time_hours": sum_workout_time_hours,
    }

    render_kpi_section("exercises", filtered_exercises_kpis, kpi_config, kpi_overrides)
    st.write(filtered_exercises)
    st.write(filtered_exercises_kpis)

    st.write("Volume and Time Chart")

    # render_altair_line_chart(volume_df, "Volume")
    st.bar_chart(
        volumes_by_exercise_df,
        x="metric_date",
        y="volume",
        color="workout_name",
    )
    # render_altair_line_chart(time_df, "Time")
except Exception as e:
    st.error(f"Error computing macro KPIs: {e}")
