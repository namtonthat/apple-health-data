"""
Pipeline: Landing Zone -> Raw Zone (Cleansed)

Reads parquet files from landing/, cleanses them, and writes to raw/.

Cleansing steps:
- Rename columns to snake_case
- Add metadata columns (load_timestamp, source_file, source_system)
- Standardize data types

Structure:
  landing/hevy/workouts/*.parquet -> raw/hevy/workouts/*.parquet
  landing/health/health_metrics/*.parquet -> raw/health/health_metrics/*.parquet
"""
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path and load .env via package __init__
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import pipelines  # noqa: F401 - loads .env on import

import pyarrow as pa
import pyarrow.parquet as pq
import s3fs


def get_s3_client() -> s3fs.S3FileSystem:
    """Create S3 filesystem client."""
    return s3fs.S3FileSystem(
        key=os.environ["AWS_ACCESS_KEY_ID"],
        secret=os.environ["AWS_SECRET_ACCESS_KEY"],
        client_kwargs={"region_name": os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-2")},
    )


def to_snake_case(name: str) -> str:
    """Convert column name to snake_case."""
    # Handle camelCase and PascalCase
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    # Replace spaces and hyphens with underscores
    s3 = re.sub(r"[\s\-]+", "_", s2)
    # Remove double underscores
    s4 = re.sub(r"_+", "_", s3)
    return s4.lower().strip("_")


def cleanse_table(
    s3: s3fs.S3FileSystem,
    bucket: str,
    source_system: str,
    table_name: str,
) -> int:
    """
    Cleanse a single table from landing to raw.

    Returns number of rows processed.
    """
    landing_path = f"{bucket}/landing/{source_system}/{table_name}"
    raw_path = f"{bucket}/raw/{source_system}/{table_name}"

    # List parquet files in landing
    try:
        files = s3.glob(f"{landing_path}/*.parquet")
    except Exception:
        files = []

    if not files:
        print(f"  No files found in {landing_path}")
        return 0

    total_rows = 0
    load_timestamp = datetime.now(timezone.utc).isoformat()

    for file_path in files:
        filename = file_path.split("/")[-1]
        output_path = f"{raw_path}/{filename}"

        # Read parquet file
        with s3.open(file_path, "rb") as f:
            table = pq.read_table(f)

        # Rename columns to snake_case
        new_names = [to_snake_case(col) for col in table.column_names]
        table = table.rename_columns(new_names)

        # Add metadata columns
        n_rows = table.num_rows
        table = table.append_column(
            "_load_timestamp",
            pa.array([load_timestamp] * n_rows, type=pa.string()),
        )
        table = table.append_column(
            "_source_file",
            pa.array([filename] * n_rows, type=pa.string()),
        )
        table = table.append_column(
            "_source_system",
            pa.array([source_system] * n_rows, type=pa.string()),
        )

        # Write to raw
        with s3.open(output_path, "wb") as f:
            pq.write_table(table, f)

        total_rows += n_rows
        print(f"  {filename}: {n_rows:,} rows -> {output_path}")

    return total_rows


def run_pipeline(source_systems: list[str] | None = None):
    """
    Run the cleanse pipeline for specified source systems.

    Args:
        source_systems: List of source systems to process (default: all)
    """
    bucket = os.environ["S3_BUCKET_NAME"]
    s3 = get_s3_client()

    # Default to all known source systems
    if source_systems is None:
        source_systems = ["hevy", "health", "strava"]

    # Table mappings per source system
    tables = {
        "hevy": ["workouts", "workouts__exercises", "workouts__exercises__sets"],
        "health": ["health_metrics"],
        "strava": ["activities"],
    }

    print("=" * 60)
    print("Cleanse Pipeline: Landing -> Raw")
    print("=" * 60)
    print(f"Bucket: {bucket}")
    print(f"Sources: {source_systems}")
    print()

    total_rows = 0

    for source in source_systems:
        print(f"\n[{source.upper()}]")

        if source not in tables:
            print(f"  Unknown source system: {source}")
            continue

        for table_name in tables[source]:
            print(f"\n  Processing: {table_name}")
            rows = cleanse_table(s3, bucket, source, table_name)
            total_rows += rows

    print("\n" + "=" * 60)
    print(f"Complete! Total rows processed: {total_rows:,}")
    print("=" * 60)

    return total_rows


if __name__ == "__main__":
    import sys

    # Allow specifying source systems via command line
    sources = sys.argv[1:] if len(sys.argv) > 1 else None
    run_pipeline(sources)
