"""Shared data loading utilities for the dashboard."""

from __future__ import annotations

import duckdb
import polars as pl

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
