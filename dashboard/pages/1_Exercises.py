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

    filtered_exercises_kpis = load_filtered_s3_data(
        conf.key_exercises_kpis,
        start_date,
        end_date,
    )

    filtered_activity = load_filtered_s3_data(
        conf.key_activity,
        start_date,
        end_date,
    )

    # Load configuration
    kpi_config = load_kpi_config()

    exercise_kpis = pl.concat([filtered_activity, filtered_exercises_kpis])

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()


st.sidebar.header("Exercise Filters")
exercise_type = st.sidebar.multiselect(
    "Workout",
    options=WORKOUT_NAMES,
)


try:
    volumes_by_exercise_df = filtered_exercises.group_by(
        ["metric_date", "workout_name", "exercise_name"],
        maintain_order=True,
    ).agg(pl.col("volume").sum())

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

    render_kpi_section("exercises", exercise_kpis, kpi_config, kpi_overrides)

    col1, col2 = st.columns(2)
    with col1:
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
    with col2:
        st.subheader("Total Volume By Exercise")
        st.write(volumes_by_exercise_df)
        # st.write(filtered_exercises_kpis)

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
    st.error(f"Error computing macro KPIs: {e}")
