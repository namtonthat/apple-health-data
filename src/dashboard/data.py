"""Shared data loading utilities for the dashboard."""

from __future__ import annotations

from datetime import date

import duckdb
import polars as pl
import streamlit as st

from dashboard.config import (
    AWS_REGION,
    S3_BUCKET,
    S3_TRANSFORMED_PREFIX,
    get_last_updated,
    get_secret,
)


@st.cache_resource(show_spinner=False)
def get_connection() -> duckdb.DuckDBPyConnection:
    """Get the shared, authenticated in-memory DuckDB connection (cached for the process).

    DuckDB connections are not thread-safe across Streamlit sessions, so callers
    must run queries via ``conn.cursor()`` rather than the connection directly.
    """
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


def filter_date_range(df: pl.DataFrame, date_col: str, start: date, end: date) -> pl.DataFrame:
    """Filter a Polars DataFrame to ``[start, end]`` inclusive on ``date_col``.

    No-op (returns ``df`` unchanged) if the frame is empty or lacks ``date_col`` --
    guards the common "loader may return an empty/columnless frame" case.
    """
    if df.height == 0 or date_col not in df.columns:
        return df
    col = pl.col(date_col).cast(pl.Date)
    return df.filter((col >= pl.lit(start)) & (col <= pl.lit(end)))


def load_parquet(
    table_name: str,
    query: str | None = None,
    params: list | None = None,
) -> pl.DataFrame:
    """Load parquet from S3 with standard error handling.

    Uses a cursor on the shared connection (see ``get_connection``) so concurrent
    Streamlit sessions don't race on the same connection object.

    Args:
        table_name: Name of the transformed table (e.g. "fct_daily_summary_recent").
        query: Custom SQL query. Use {path} as placeholder for the S3 path.
               If None, loads the entire table with ``SELECT * FROM read_parquet(...)``
        params: Optional query parameters for parameterised queries.
    """
    conn = get_connection()
    cursor = conn.cursor()
    s3_path = get_s3_path(table_name)

    if query is None:
        query = f"SELECT * FROM read_parquet('{s3_path}') ORDER BY 1"
    else:
        query = query.replace("{path}", s3_path)

    try:
        if params:
            return pl.from_arrow(cursor.execute(query, params).fetch_arrow_table())
        return pl.from_arrow(cursor.execute(query).fetch_arrow_table())
    except duckdb.Error as e:
        if "No files found" in str(e):
            return pl.DataFrame()
        raise
    finally:
        cursor.close()


# Cache TTL note: data is refreshed once daily by CI (13:00 UTC), not hourly. Each
# public load_* function below fetches the S3 LastModified of the daily summary
# (cached 60s, see config.get_last_updated) and forwards it as the cache key on the
# private _cached implementation -- so the cache invalidates exactly when the
# daily refresh writes new data, instead of on an arbitrary wall-clock TTL.


@st.cache_data(show_spinner="Loading health data...")
def _load_daily_summary(_last_updated: str) -> pl.DataFrame:
    return load_parquet(
        "fct_daily_summary",
        query=(
            "SELECT date, sleep_hours, sleep_deep_hours, sleep_rem_hours, sleep_light_hours,"
            " resting_hr_bpm, hrv_ms, vo2_max, weight_kg, steps, walking_asymmetry_pct,"
            " meditation_minutes, protein_g, carbs_g, fat_g, fiber_g, water_ml,"
            " logged_calories, macro_calories, had_strength_workout, total_volume_kg,"
            " avg_rpe, workout_duration_minutes"
            " FROM read_parquet('{path}') ORDER BY date"
        ),
    )


def load_daily_summary() -> pl.DataFrame:
    """Load the daily summary table (cached; invalidates on the daily data refresh)."""
    return _load_daily_summary(get_last_updated())


@st.cache_data(show_spinner="Loading weight averages...")
def _load_weight_rolling_averages(_last_updated: str) -> pl.DataFrame:
    return load_parquet(
        "fct_weight_rolling_averages",
        query=(
            "SELECT date, avg_7d, avg_14d, avg_30d, avg_60d, avg_120d"
            " FROM read_parquet('{path}') ORDER BY date DESC"
        ),
    )


def load_weight_rolling_averages() -> pl.DataFrame:
    """Load rolling weight averages (cached; invalidates on the daily data refresh)."""
    return _load_weight_rolling_averages(get_last_updated())


@st.cache_data(show_spinner="Loading workout data...")
def _load_workouts(_last_updated: str) -> pl.DataFrame:
    return load_parquet(
        "fct_workouts",
        query=(
            "SELECT workout_date, workout_name, started_at, ended_at, workout_duration_minutes"
            " FROM read_parquet('{path}') ORDER BY workout_date DESC, started_at DESC"
        ),
    )


def load_workouts() -> pl.DataFrame:
    """Load one row per workout (session grain) with name, times, and duration."""
    return _load_workouts(get_last_updated())


@st.cache_data(show_spinner="Loading readiness data...")
def _load_training_readiness(_last_updated: str) -> pl.DataFrame:
    return load_parquet(
        "fct_training_readiness",
        query=(
            "SELECT date, readiness_score, hrv_score, rhr_score, sleep_score, deep_score"
            " FROM read_parquet('{path}') ORDER BY date"
        ),
    )


def load_training_readiness() -> pl.DataFrame:
    """Load training readiness scores (cached; invalidates on the daily data refresh)."""
    return _load_training_readiness(get_last_updated())


@st.cache_data(show_spinner="Loading workout sets...")
def _load_workout_sets(_last_updated: str) -> pl.DataFrame:
    return load_parquet(
        "fct_workout_sets",
        query=(
            "SELECT workout_date, workout_name, exercise_name, set_number,"
            " weight_kg, reps, volume_kg, est_1rm, rpe, set_type, started_at, exercise_order"
            " FROM read_parquet('{path}')"
            " ORDER BY workout_date DESC, started_at DESC, exercise_order, set_number"
        ),
    )


def load_workout_sets() -> pl.DataFrame:
    """Load workout sets with the pre-computed est_1rm column."""
    return _load_workout_sets(get_last_updated())


@st.cache_data(show_spinner="Loading lift PRs...")
def _load_big3_prs(_last_updated: str) -> pl.DataFrame:
    return load_parquet(
        "fct_big3_prs",
        query=(
            "SELECT lift, best_e1rm, best_weight_kg, best_reps, pr_date"
            " FROM read_parquet('{path}') ORDER BY lift"
        ),
    )


def load_big3_prs() -> pl.DataFrame:
    """Load all-time best estimated 1RM per Big 3 lift."""
    return _load_big3_prs(get_last_updated())


@st.cache_data(show_spinner="Loading personal bests...")
def _load_personal_bests(_last_updated: str) -> pl.DataFrame:
    return load_parquet(
        "fct_personal_bests",
        query=(
            "SELECT squat_pr_kg, bench_pr_kg, deadlift_pr_kg, total_pr_kg, last_competition"
            " FROM read_parquet('{path}')"
        ),
    )


def load_personal_bests() -> pl.DataFrame:
    """Load competition personal bests from OpenPowerlifting data."""
    return _load_personal_bests(get_last_updated())


@st.cache_data(show_spinner="Loading 1RM totals...")
def _load_e1rm_rolling_total(_last_updated: str) -> pl.DataFrame:
    return load_parquet(
        "fct_e1rm_rolling_total",
        query=(
            "SELECT workout_date, squat_e1rm, bench_e1rm, deadlift_e1rm, estimated_total"
            " FROM read_parquet('{path}') ORDER BY workout_date"
        ),
    )


def load_e1rm_rolling_total() -> pl.DataFrame:
    """Load rolling estimated 1RM totals for the Big 3."""
    return _load_e1rm_rolling_total(get_last_updated())


@st.cache_data(show_spinner="Loading Strava activities...")
def _load_strava_activities(_last_updated: str) -> pl.DataFrame:
    return load_parquet(
        "fct_strava_activities",
        query=(
            "SELECT activity_date, activity_name, activity_type, distance_km,"
            " moving_time_minutes, elevation_gain_m, avg_heartrate, avg_pace_min_per_km,"
            " max_heartrate, pr_count"
            " FROM read_parquet('{path}') ORDER BY activity_date DESC"
        ),
    )


def load_strava_activities() -> pl.DataFrame:
    """Load Strava activities (cached; filter by date in the page)."""
    return _load_strava_activities(get_last_updated())
