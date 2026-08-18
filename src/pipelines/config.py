"""Shared configuration and factory functions for all pipelines."""

import os
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import dlt
import duckdb
import s3fs
from dlt.destinations import filesystem


def get_bucket() -> str:
    """Get S3 bucket name from environment."""
    return os.environ["S3_BUCKET_NAME"]


def get_region() -> str:
    """Get AWS region from environment."""
    return os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-2")


@lru_cache(maxsize=1)
def _default_s3_client() -> s3fs.S3FileSystem:
    """The plain (no extra kwargs) S3 client, memoized — fresh S3FileSystem per
    call was measurable overhead given how often pipelines reach for one."""
    return s3fs.S3FileSystem(
        key=os.environ["AWS_ACCESS_KEY_ID"],
        secret=os.environ["AWS_SECRET_ACCESS_KEY"],
        client_kwargs={"region_name": get_region()},
    )


def get_s3_client(**s3_kwargs) -> s3fs.S3FileSystem:
    """Create S3 filesystem client.

    The common no-kwargs call is memoized (see `_default_s3_client`). Calls with
    extra kwargs (e.g. `s3_additional_kwargs={"ACL": "public-read"}`) bypass the
    cache and always build a fresh client, since those kwargs can be unhashable.

    Args:
        **s3_kwargs: Extra kwargs passed to S3FileSystem
                     (e.g. s3_additional_kwargs={"ACL": "public-read"})
    """
    if not s3_kwargs:
        return _default_s3_client()

    return s3fs.S3FileSystem(
        key=os.environ["AWS_ACCESS_KEY_ID"],
        secret=os.environ["AWS_SECRET_ACCESS_KEY"],
        client_kwargs={"region_name": get_region()},
        **s3_kwargs,
    )


@lru_cache(maxsize=1)
def get_duckdb_connection() -> duckdb.DuckDBPyConnection:
    """Get DuckDB connection configured for S3 and Delta access.

    Memoized: repeated calls return the same connection instead of opening a new
    in-memory DuckDB + re-installing the delta extension each time.
    """
    conn = duckdb.connect(":memory:")
    conn.execute("INSTALL delta; LOAD delta;")
    # OR REPLACE keeps this idempotent — a second call (e.g. from a cache miss
    # after a fork, or before this function was memoized) must not error on an
    # already-named secret.
    conn.execute(f"""
        CREATE OR REPLACE SECRET s3_secret (
            TYPE s3,
            KEY_ID '{os.environ["AWS_ACCESS_KEY_ID"]}',
            SECRET '{os.environ["AWS_SECRET_ACCESS_KEY"]}',
            REGION '{get_region()}'
        )
    """)
    return conn


def get_s3_destination():
    """Configure S3 filesystem destination for landing zone (Delta tables)."""
    return filesystem(
        bucket_url=f"s3://{get_bucket()}/landing",
        credentials={
            "aws_access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
            "aws_secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
            "region_name": get_region(),
        },
    )


def run_s3_pipeline(name: str, dataset: str, source, extraction_date: str | None = None):
    """Run a dlt pipeline that loads data to S3 landing zone.

    Args:
        name: Pipeline name (e.g. "hevy_to_landing")
        dataset: Dataset name / S3 prefix under landing/ (e.g. "hevy")
        source: dlt source to extract from
        extraction_date: Cosmetic label for this load (YYYY-MM-DD), defaults to
            today. It is only printed in the run summary — it does not filter,
            window, or otherwise affect which source data gets extracted.
    """
    if extraction_date is None:
        extraction_date = datetime.now(ZoneInfo("Australia/Melbourne")).date().isoformat()

    bucket = get_bucket()
    destination_path = f"s3://{bucket}/landing/{dataset}"

    pipeline = dlt.pipeline(
        pipeline_name=name,
        destination=get_s3_destination(),
        dataset_name=dataset,
        pipelines_dir=os.environ.get("DLT_PIPELINE_DIR", ".dlt_pipelines"),
    )

    load_info = pipeline.run(source, table_format="delta")

    label = name.replace("_to_landing", "").replace("_", " ").title()
    print("=" * 60)
    print(f"{label} -> Landing Zone Complete")
    print("=" * 60)
    print(f"Extraction date: {extraction_date}")
    print(f"Destination: {destination_path}/")
    print(f"\nLoad info: {load_info}")

    if load_info.load_packages:
        print("\nDelta tables loaded:")
        for table in load_info.load_packages[0].schema.tables:
            if not table.startswith("_dlt"):
                print(f"  - {table}/ (Delta)")

    return load_info
