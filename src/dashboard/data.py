"""Shared data loading utilities for the dashboard."""

from __future__ import annotations

from datetime import timedelta

import duckdb
import polars as pl
import streamlit as st

from dashboard.config import AWS_REGION, S3_BUCKET, S3_TRANSFORMED_PREFIX, get_secret


def get_connection() -> duckdb.DuckDBPyConnection:
    """Get fresh DuckDB connection configured for S3 access."""
    conn = duckdb.connect(":memory:")
    access_key = get_secret("AWS_ACCESS_KEY_ID")
    secret_key = get_secret("AWS_SECRET_ACCESS_KEY")
    conn.execute(f"SET s3_region = '{AWS_REGION}'")
    conn.execute(f"SET s3_access_key_id = '{access_key}'")
    conn.execute(f"SET s3_secret_access_key = '{secret_key}'")
    return conn


def get_s3_path(table_name: str) -> str:
    """Build S3 path for a transformed table."""
    return f"s3://{S3_BUCKET}/{S3_TRANSFORMED_PREFIX}/{table_name}"


def load_parquet(
    table_name: str,
    query: str | None = None,
    params: list | None = None,
) -> pl.DataFrame:
    """Load parquet from S3 with standard error handling.

    Args:
        table_name: Name of the transformed table (e.g. "fct_daily_summary_recent").
        query: Custom SQL query. Use {path} as placeholder for the S3 path.
               If None, loads the entire table with ``SELECT * FROM read_parquet(...)``
        params: Optional query parameters for parameterised queries.
    """
    conn = get_connection()
    s3_path = get_s3_path(table_name)

    if query is None:
        query = f"SELECT * FROM read_parquet('{s3_path}') ORDER BY 1"
    else:
        query = query.replace("{path}", s3_path)

    try:
        if params:
            return pl.from_arrow(conn.execute(query, params).fetch_arrow_table())
        return pl.from_arrow(conn.execute(query).fetch_arrow_table())
    except Exception as e:
        if "No files found" in str(e):
            return pl.DataFrame()
        raise
    finally:
        conn.close()


@st.cache_data(ttl=timedelta(hours=1), show_spinner="Loading health data...")
def load_daily_summary() -> pl.DataFrame:
    """Load the daily summary table (cached across reruns)."""
    return load_parquet("fct_daily_summary")


@st.cache_data(ttl=timedelta(hours=1), show_spinner="Loading weight averages...")
def load_weight_rolling_averages() -> pl.DataFrame:
    """Load rolling weight averages (cached across reruns)."""
    return load_parquet("fct_weight_rolling_averages")


@st.cache_data(ttl=timedelta(hours=1), show_spinner="Loading workout data...")
def load_workouts() -> pl.DataFrame:
    """Load one row per workout (session grain) with name, times, and duration."""
    return load_parquet("fct_workouts")


@st.cache_data(ttl=timedelta(hours=1), show_spinner="Loading readiness data...")
def load_training_readiness() -> pl.DataFrame:
    """Load training readiness scores."""
    return load_parquet("fct_training_readiness")


@st.cache_data(ttl=timedelta(hours=1), show_spinner="Loading workout sets...")
def load_workout_sets() -> pl.DataFrame:
    """Load workout sets with the pre-computed est_1rm column."""
    return load_parquet(
        "fct_workout_sets",
        query=(
            "SELECT workout_date, workout_name, exercise_name, set_number,"
            " weight_kg, reps, volume_kg, est_1rm, rpe, set_type, started_at, exercise_order"
            " FROM read_parquet('{path}')"
            " ORDER BY workout_date DESC, started_at DESC, exercise_order, set_number"
        ),
    )


@st.cache_data(ttl=timedelta(hours=1), show_spinner="Loading lift PRs...")
def load_big3_prs() -> pl.DataFrame:
    """Load all-time best estimated 1RM per Big 3 lift."""
    return load_parquet("fct_big3_prs")


@st.cache_data(ttl=timedelta(hours=1), show_spinner="Loading personal bests...")
def load_personal_bests() -> pl.DataFrame:
    """Load competition personal bests from OpenPowerlifting data."""
    return load_parquet("fct_personal_bests")


@st.cache_data(ttl=timedelta(hours=1), show_spinner="Loading 1RM totals...")
def load_e1rm_rolling_total() -> pl.DataFrame:
    """Load rolling estimated 1RM totals for the Big 3."""
    return load_parquet("fct_e1rm_rolling_total")


@st.cache_data(ttl=timedelta(hours=1), show_spinner="Loading Strava activities...")
def load_strava_activities() -> pl.DataFrame:
    """Load Strava activities (cached; filter by date in the page)."""
    return load_parquet("fct_strava_activities")
