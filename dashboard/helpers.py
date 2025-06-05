"""
Helper functions module for the dashboard application.

This module contains functions to read data from AWS S3 (in Parquet format) using Polars
"""

import logging
from datetime import date, datetime, time, timedelta
from typing import Optional

import conf
import polars as pl
import pytz
import streamlit as st
from powerlifting_functions import calculate_dots, estimate_one_rep_max

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@st.cache_data
def load_filtered_s3_data(
    s3_key: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pl.DataFrame:
    s3_path = f"s3://{conf.s3_bucket}/{s3_key}"
    df = pl.read_parquet(s3_path)
    if start_date:
        df = df.filter(pl.col("metric_date") >= start_date)
    if end_date:
        df = df.filter(pl.col("metric_date") <= end_date)

    return df.with_columns(
        pl.col("metric_date").dt.strftime("%Y-%m-%d").alias("metric_date")
    )


def convert_column_to_timezone(
    df: pl.DataFrame, column: str, tz: str = conf.timezone
) -> pl.DataFrame:
    """
    Converts a Polars datetime column to a specific timezone using Python datetime + pytz.

    Note: Polars doesn't natively support timezone-aware datetime objects,
    so this uses a Python UDF.
    """

    required_tz = pytz.timezone(tz)

    return df.with_columns(
        pl.col(column).map_elements(
            lambda dt: dt.astimezone(required_tz).replace(tzinfo=None),
            return_dtype=pl.Datetime,
        )
    )


def compute_avg_sleep_time_from_midnight(
    df: pl.DataFrame, time_col: str = "sleep_times"
) -> datetime | None:
    """
    Computes the average sleep time as an offset from midnight,
    treating times before midnight as negative offsets.

    Args:
        df: A Polars DataFrame with a datetime column (naive, in local time).
        time_col: Name of the column with local sleep times.

    Returns:
        A datetime.datetime object representing the average sleep time (on today's date).
    """
    # Extract times as list of Python datetime objects
    times = df[time_col].to_list()
    if not times:
        return None

    offsets = []
    for dt in times:
        midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        offset = dt - midnight

        # If the time is "late night" before midnight, treat as negative offset from midnight
        if offset > timedelta(hours=12):
            offset -= timedelta(days=1)

        offsets.append(offset)

    # Compute average offset
    avg_offset = sum(offsets, timedelta()) / len(offsets)

    # Return as a datetime today + offset (for display)
    midnight_today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight_today + avg_offset


def compute_avg_sleep_time(
    df: pl.DataFrame, time_col: str = "sleep_times"
) -> datetime | None:
    times = df[time_col].to_list()

    if not times:
        return None

    SECONDS_IN_DAY = 24 * 60 * 60
    anchor_hour = 19  # 7 PM

    offsets = []
    for dt in times:
        seconds = dt.hour * 3600 + dt.minute * 60 + dt.second

        # Shift times so sleep period stays together around midnight
        shifted_seconds = (seconds - anchor_hour * 3600) % SECONDS_IN_DAY
        offsets.append(shifted_seconds)

    avg_shifted = sum(offsets) / len(offsets)

    # Reverse the shift
    avg_seconds = (avg_shifted + anchor_hour * 3600) % SECONDS_IN_DAY

    midnight_today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight_today + timedelta(seconds=avg_seconds)


def sidebar_datetime_filter() -> tuple[datetime, datetime]:
    """
    Render a shared sidebar date filter component and return start/end date.
    """
    st.sidebar.header("Date Filter")
    filter_mode = st.sidebar.radio("Filter Mode", ("Quick Filter", "Custom Range"))

    today = datetime.today().date()

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
        start_date = st.sidebar.date_input(
            "Start Date", value=today - timedelta(days=30)
        )
        end_date = st.sidebar.date_input("End Date", value=today)

    # Create datetime objects for filtering: start at midnight, end at 23:59:59
    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time(23, 59, 59))

    st.sidebar.caption(f"Showing data from `{start_date}` to `{end_date}`")
    return start_dt, end_dt


def compute_latest_one_rep_maxes(
    df: pl.DataFrame, bodyweight_kg: float, sex: str = "male"
) -> pl.DataFrame:
    """
    Computes the latest powerlifting-style record from the input DataFrame,
    including estimated 1RMs and DOTS score, returned as a single-row summary.

    Parameters:
        df (pl.DataFrame): Input training log with at least ['date', 'exercise_name', 'weight_kg', 'reps'] columns.
        bodyweight_kg (float): Athlete's bodyweight in kilograms.
        sex (str): 'male' or 'female' for DOTS calculation.

    Returns:
        pl.DataFrame: A one-row DataFrame with Competition Date, 1RMs, Total, and DOTS.
    """
    sbd_df = filter_for_sbd(df)
    one_rep_maxes = estimate_one_rep_maxes(sbd_df)

    result_dict = format_result_row(one_rep_maxes, bodyweight_kg, sex)
    return pl.DataFrame([result_dict])


def filter_for_sbd(df: pl.DataFrame) -> pl.DataFrame:
    """
    Filters the DataFrame to rows matching the required exercises
    """
    rename_map_keys = ["sumo deadlift", "squat (barbell)", "bench press (barbell)"]
    return df.filter(
        pl.col("exercise_name").str.contains_any(
            rename_map_keys, ascii_case_insensitive=True
        )
    ).select(["exercise_name", "weight_kg", "reps"])


def estimate_one_rep_maxes(df: pl.DataFrame) -> dict:
    """
    Estimates 1RM for each lift and returns a dict: {lift: 1RM}.
    """
    rename_map = {
        "sumo deadlift": "deadlift",
        "squat (barbell)": "squat",
        "bench press (barbell)": "bench",
    }

    est_1rms = [estimate_one_rep_max(row[1], row[2]) for row in df.iter_rows()]
    df = df.with_columns([pl.Series("est_1rm", est_1rms)])

    df = df.with_columns(
        [
            pl.col("exercise_name")
            .str.to_lowercase()
            .replace(rename_map)
            .alias("exercise_name")
        ]
    )

    return {
        row["exercise_name"]: row["est_1rm"]
        for row in df.group_by("exercise_name").agg(pl.col("est_1rm").max()).to_dicts()
    }


def format_result_row(one_rep_maxes: dict, bodyweight_kg: float, sex: str) -> dict:
    """
    Formats the final result row dict including DOTS score.
    """
    squat = one_rep_maxes.get("squat", 0)
    bench = one_rep_maxes.get("bench", 0)
    deadlift = one_rep_maxes.get("deadlift", 0)
    total = squat + bench + deadlift

    return {
        "Squat (kg)": squat,
        "Bench (kg)": bench,
        "Deadlift (kg)": deadlift,
        "Total (kg)": total,
        "DOTS": calculate_dots(total, bodyweight_kg, sex),
    }
