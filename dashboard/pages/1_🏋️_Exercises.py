"""
Streamlit dashboard for apple-health-data
"""

import os
from datetime import datetime

import conf
import polars as pl
import streamlit as st
from dotenv import load_dotenv
from graphing import render_altair_line_chart
from helpers import (
    compute_latest_one_rep_maxes,
    load_filtered_s3_data,
    sidebar_datetime_filter,
)
from kpi import load_kpi_config, render_kpi_section

load_dotenv()
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
OPENPOWERLIFTING_USERNAME = os.getenv("OPENPOWERLIFTING_USERNAME")


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

if exercise_type:
    filtered_exercises = filtered_exercises.filter(
        pl.col("workout_name").is_in(exercise_type)
    )


def is_valid_df(df):
    """Validate dataframe for rendering"""
    return df is not None and df.shape[0] > 0


one_rep_max_df = pl.DataFrame()
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

best_meet_records = None
try:
    unfiltered_openpowerlifting = load_filtered_s3_data(
        conf.key_openpowerlifting,
    )
    if is_valid_df(unfiltered_openpowerlifting):
        best_meet = unfiltered_openpowerlifting.select(pl.col("Dots").max())
        best_meet_records = (
            unfiltered_openpowerlifting.filter(pl.col("Dots") == best_meet.item())
            .select(
                [
                    "metric_date",
                    "best3_squat_kg",
                    "best3_bench_kg",
                    "best3_deadlift_kg",
                    "total_kg",
                    "Dots",
                ]
            )
            .rename(
                {
                    "metric_date": "Competition Date",
                    "best3_squat_kg": "Squat (kg)",
                    "best3_bench_kg": "Bench (kg)",
                    "best3_deadlift_kg": "Deadlift (kg)",
                    "Dots": "DOTS",
                    "total_kg": "Total (kg)",
                }
            )
        )

except Exception as e:
    st.error(f"Error collecting openpowerlifting data: {e}")


if is_valid_df(best_meet_records):
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🧮 Estimated One Rep Max")

        st.write(
            f"For the period between `{start_date.date()}` and `{end_date.date()}`"
        )
        average_weight = filtered_health.filter(
            pl.col("metric_name") == "weight_body_mass"
        )["quantity"].mean()

        one_rep_max_df = compute_latest_one_rep_maxes(
            df=filtered_exercises,
            bodyweight_kg=average_weight,
        )
        st.write(one_rep_max_df)
    with col2:
        st.subheader("🏆 Best Competition Record")
        st.write(
            f"Sourced from [here](http://openpowerlifting.org/u/{OPENPOWERLIFTING_USERNAME})"
        )
        st.write(best_meet_records)

    st.subheader("🛠️ Exercise Metrics")
    render_kpi_section("exercises", filtered_health, kpi_config, kpi_overrides)

else:
    st.subheader("🛠️ Exercise Metrics")
    render_kpi_section("exercises", filtered_health, kpi_config, kpi_overrides)


try:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Total Volume By Exercise")
        volumes_by_exercise_df_output = volumes_by_exercise_df.rename(
            {
                "metric_date": "date",
                "workout_name": "workout",
                "exercise_name": "exercise",
                "quantity": "volume",
            }
        )

        st.write(volumes_by_exercise_df_output)
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
        ).rename(
            {
                "metric_date": "date",
                "exercise_name": "exercise",
                "set_type": "set type",
                "weight_kg": "weight (kg)",
            },
        )
        st.write(detailed_exercises)

    st.write("Volume and Time Charts")

    if not exercise_type:
        col1, col2 = st.columns(2)
        with col1:
            st.bar_chart(
                volumes_by_exercise_df,
                x="metric_date",
                y="quantity",
                x_label="Date",
                y_label="Volume (kg)",
                color="exercise_name",
            )
        with col2:
            render_altair_line_chart(
                time_df,
                title="Time (mins)",
                use_min_max_scale=False,
            )
    else:
        st.bar_chart(
            volumes_by_exercise_df,
            x="metric_date",
            y="quantity",
            x_label="Date",
            y_label="Volume (kg)",
            color="exercise_name",
        )

except Exception as e:
    st.error(f"Error computing exercise KPIs: {e}")
