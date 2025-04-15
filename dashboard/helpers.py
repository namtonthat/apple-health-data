"""
Helper functions module for the dashboard application.

This module contains functions to read data from AWS S3 (in Parquet format) using Polars
"""

import logging
from datetime import date, datetime, time, timedelta
from pathlib import Path

import conf
import duckdb
import polars as pl
import pytz
import streamlit as st
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def filter_data(df, start_date, end_date):
    """Filter a Polars DataFrame by date and reformat the metric_date column."""
    return df.filter(
        (pl.col("metric_date") >= start_date) & (pl.col("metric_date") <= end_date)
    ).with_columns(pl.col("metric_date").dt.strftime("%Y-%m-%d").alias("metric_date"))


@st.cache_data
def load_filtered_s3_data(
    s3_key: str,
    start_date: date,
    end_date: date,
):
    s3_path = f"s3://{conf.s3_bucket}/{s3_key}"
    unfiltered_df = pl.read_parquet(s3_path)
    return filter_data(unfiltered_df, start_date, end_date)


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
) -> datetime:
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


def compute_avg_sleep_time(df: pl.DataFrame, time_col: str = "sleep_times") -> datetime:
    times = df[time_col].to_list()

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


### Reflections


def load_questions_from_yaml():
    yaml_path: Path = Path(__file__).parent / "questions.yaml"
    with Path.open(yaml_path) as file:
        return yaml.safe_load(file)


DB_NAME = "responses.duckdb"


def init_db():
    conn = duckdb.connect(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS form_entries (
            date TIMESTAMP,
            response_type VARCHAR,
            content TEXT
        )
    """)
    conn.close()


def insert_entry(date, response_type, content):
    conn = duckdb.connect(DB_NAME)
    conn.execute(
        "INSERT INTO form_entries VALUES (?, ?, ?)", (date, response_type, content)
    )
    conn.close()


def get_all_entries():
    conn = duckdb.connect(DB_NAME)
    result = conn.execute("SELECT * FROM form_entries ORDER BY date DESC").fetchall()
    conn.close()
    return result
