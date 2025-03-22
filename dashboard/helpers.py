"""
Helper functions module for the dashboard application.

This module contains functions to read data from AWS S3 (in Parquet format) using Polars
"""

import io
import logging
from datetime import date, datetime, timedelta

import boto3
import conf
import polars as pl
import pytz
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def read_parquet_from_s3(bucket: str, key: str) -> pl.DataFrame:
    """
    Read a Parquet file from AWS S3 and return a Polars DataFrame.

    Args:
        bucket: The S3 bucket name.
        key: The S3 key/path of the Parquet file.

    Returns:
        A Polars DataFrame containing the data.
    """
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=bucket, Key=key)
    logger.info("Reading Parquet data from s3://%s/%s", bucket, key)
    data = io.BytesIO(obj["Body"].read())
    return pl.read_parquet(data)


def filter_data(df, start_date, end_date):
    """Filter a Polars DataFrame by date and reformat the metric_date column."""
    return df.filter(
        (pl.col("metric_date") >= start_date) & (pl.col("metric_date") <= end_date)
    ).with_columns(pl.col("metric_date").dt.strftime("%Y-%m-%d").alias("metric_date"))


@st.cache_data
def load_data_by_key(s3_key: str, start_date: date, end_date: date):
    unfiltered_df = read_parquet_from_s3(conf.s3_bucket, s3_key)
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


def sidebar_date_filter() -> tuple[date, date]:
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

    st.sidebar.caption(f"Showing data from `{start_date}` to `{end_date}`")
    return start_date, end_date
