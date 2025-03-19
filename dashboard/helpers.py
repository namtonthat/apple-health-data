"""
Helper functions module for the dashboard application.

This module contains functions to read data from AWS S3 (in Parquet format)
using Polars, and functions to load and insert reflections data into DuckDB.
"""

import io
import logging
from typing import Dict

import boto3
import duckdb
import polars as pl

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


def create_reflections_table(db_path: str) -> None:
    """
    Create the reflections table in DuckDB if it does not exist.

    Args:
        db_path: Path to the DuckDB database file.
    """
    con = duckdb.connect(database=db_path, read_only=False)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS reflections (
                week VARCHAR,
                q1 VARCHAR,
                q2 VARCHAR,
                q3 VARCHAR,
                q4 VARCHAR,
                q5 VARCHAR,
                timestamp VARCHAR
            )
            """
        )
        logger.info("Reflections table ensured in %s", db_path)
    except Exception as e:
        logger.error("Error creating reflections table: %s", e)
        raise
    finally:
        con.close()


def load_reflections_from_duckdb(db_path: str) -> pl.DataFrame:
    """
    Load reflections data from a DuckDB database and return a Polars DataFrame.

    If the table does not exist, it is created first.

    Args:
        db_path: Path to the DuckDB database file.

    Returns:
        A Polars DataFrame with reflections data.
    """
    # Ensure the reflections table exists.
    create_reflections_table(db_path)

    con = duckdb.connect(database=db_path, read_only=False)
    try:
        # Use DuckDB's Arrow integration to fetch data.
        arrow_table = con.execute("SELECT * FROM reflections").arrow()
        df = pl.from_arrow(arrow_table)
        logger.info("Loaded reflections data from %s", db_path)
    except Exception as e:
        logger.error("Error loading reflections: %s", e)
        df = pl.DataFrame()
    finally:
        con.close()
    return df


def insert_reflections_into_duckdb(db_path: str, new_entry: Dict[str, str]) -> None:
    """
    Insert a new reflections entry into the DuckDB database.

    Assumes the reflections table has columns: week, q1, q2, q3, q4, q5, timestamp.

    Args:
        db_path: Path to the DuckDB database file.
        new_entry: A dictionary representing the new reflections entry.
    """
    con = duckdb.connect(database=db_path, read_only=False)
    columns = ", ".join(new_entry.keys())
    values = ", ".join(f"'{v}'" for v in new_entry.values())
    query = f"INSERT INTO reflections ({columns}) VALUES ({values})"
    logger.info("Executing query: %s", query)
    con.execute(query)
    con.close()
