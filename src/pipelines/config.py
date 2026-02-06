"""Shared configuration and factory functions for all pipelines."""
import os
from datetime import date

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


def get_s3_client(**s3_kwargs) -> s3fs.S3FileSystem:
    """Create S3 filesystem client.

    Args:
        **s3_kwargs: Extra kwargs passed to S3FileSystem
                     (e.g. s3_additional_kwargs={"ACL": "public-read"})
    """
    return s3fs.S3FileSystem(
        key=os.environ["AWS_ACCESS_KEY_ID"],
        secret=os.environ["AWS_SECRET_ACCESS_KEY"],
        client_kwargs={"region_name": get_region()},
        **s3_kwargs,
    )


def get_duckdb_connection() -> duckdb.DuckDBPyConnection:
    """Get DuckDB connection configured for S3 access."""
    conn = duckdb.connect(":memory:")
    conn.execute(f"SET s3_region = '{get_region()}'")
    conn.execute(f"SET s3_access_key_id = '{os.environ['AWS_ACCESS_KEY_ID']}'")
    conn.execute(f"SET s3_secret_access_key = '{os.environ['AWS_SECRET_ACCESS_KEY']}'")
    return conn


def get_s3_destination(extraction_date: str):
    """Configure S3 filesystem destination for landing zone.

    Files land as: landing/{dataset}/{table_name}/{date}.{file_id}.parquet
    """
    return filesystem(
        bucket_url=f"s3://{get_bucket()}/landing",
        credentials={
            "aws_access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
            "aws_secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
            "region_name": get_region(),
        },
        layout="{table_name}/" + extraction_date + ".{file_id}.{ext}",
    )


def run_s3_pipeline(name: str, dataset: str, source, extraction_date: str | None = None):
    """Run a dlt pipeline that loads data to S3 landing zone.

    Args:
        name: Pipeline name (e.g. "hevy_to_landing")
        dataset: Dataset name / S3 prefix under landing/ (e.g. "hevy")
        source: dlt source to extract from
        extraction_date: Date string (YYYY-MM-DD), defaults to today
    """
    if extraction_date is None:
        extraction_date = date.today().isoformat()

    bucket = get_bucket()
    destination_path = f"s3://{bucket}/landing/{dataset}"

    pipeline = dlt.pipeline(
        pipeline_name=name,
        destination=get_s3_destination(extraction_date),
        dataset_name=dataset,
        pipelines_dir=os.environ.get("DLT_PIPELINE_DIR", ".dlt_pipelines"),
    )

    load_info = pipeline.run(
        source,
        loader_file_format="parquet",
    )

    label = name.replace("_to_landing", "").replace("_", " ").title()
    print("=" * 60)
    print(f"{label} -> Landing Zone Complete")
    print("=" * 60)
    print(f"Extraction date: {extraction_date}")
    print(f"Destination: {destination_path}/")
    print(f"\nLoad info: {load_info}")

    if load_info.load_packages:
        print("\nTables loaded:")
        for table in load_info.load_packages[0].schema.tables:
            if not table.startswith("_dlt"):
                print(f"  - {table}/{extraction_date}.parquet")

    return load_info
