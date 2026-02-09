"""
Pipeline: Landing Zone -> Raw Zone (Cleansed)

Reads parquet files from landing/, cleanses them, and writes to raw/.

Cleansing steps:
- Rename columns to snake_case
- Add metadata columns (load_timestamp, source_file, source_system)
- Standardize data types

Structure:
  landing/hevy/workouts/*.parquet -> raw/hevy/workouts/*.parquet
  landing/health/health_metrics/*.parquet -> raw/health/health_metrics/YYYY-MM.parquet (monthly)
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path and load .env via package __init__
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import s3fs

import pipelines  # noqa: F401 - loads .env on import
from pipelines.config import get_bucket, get_s3_client


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


def cleanse_health_monthly(
    s3: s3fs.S3FileSystem,
    bucket: str,
    months_to_reprocess: int = 2,
) -> int:
    """
    Cleanse health metrics from landing to raw, organized by metric_date month.

    Reads ALL landing parquet files, concatenates them, partitions by
    metric_date month (YYYY-MM), and writes one parquet file per month
    to raw. Only rewrites files for the most recent N months on incremental
    runs; first run writes all months.

    Returns number of rows processed.
    """
    landing_path = f"{bucket}/landing/health/health_metrics"
    raw_path = f"{bucket}/raw/health/health_metrics"

    # List all parquet files in landing
    try:
        files = s3.glob(f"{landing_path}/*.parquet")
    except Exception:
        files = []

    if not files:
        print(f"  No files found in {landing_path}")
        return 0

    print(f"  Reading {len(files)} landing files...")

    # Read and concatenate all landing files
    tables = []
    for file_path in files:
        with s3.open(file_path, "rb") as f:
            table = pq.read_table(f)
        tables.append(table)

    combined = pa.concat_tables(tables, promote_options="default")

    # Rename columns to snake_case
    new_names = [to_snake_case(col) for col in combined.column_names]
    combined = combined.rename_columns(new_names)

    # Extract month (YYYY-MM) from metric_date column
    metric_dates = combined.column("metric_date").to_pylist()
    months = [d[:7] if d and len(d) >= 7 else "unknown" for d in metric_dates]
    combined = combined.append_column("_month", pa.array(months, type=pa.string()))

    # Determine which months to write
    unique_months = sorted(set(m for m in months if m != "unknown"))
    if not unique_months:
        print("  No valid metric_date values found")
        return 0

    # First run detection: if no monthly files exist in raw, write all months
    existing_monthly = []
    try:
        existing_raw = s3.glob(f"{raw_path}/*.parquet")
        existing_monthly = [f for f in existing_raw if re.match(r".*\d{4}-\d{2}\.parquet$", f)]
    except Exception:
        pass

    if not existing_monthly:
        months_to_write = unique_months
        print(f"  First run detected - writing all {len(months_to_write)} months")
    else:
        months_to_write = unique_months[-months_to_reprocess:]
        print(f"  Incremental run - reprocessing months: {months_to_write}")

    print(f"  Total months: {len(unique_months)} ({unique_months[0]} to {unique_months[-1]})")

    load_timestamp = datetime.now(timezone.utc).isoformat()
    total_rows = 0

    for month in months_to_write:
        # Filter to this month
        mask = pc.equal(combined.column("_month"), month)
        month_table = combined.filter(mask)

        # Drop the temporary _month column
        col_idx = month_table.schema.get_field_index("_month")
        month_table = month_table.remove_column(col_idx)

        # Add metadata columns
        n_rows = month_table.num_rows
        month_table = month_table.append_column(
            "_load_timestamp",
            pa.array([load_timestamp] * n_rows, type=pa.string()),
        )
        month_table = month_table.append_column(
            "_source_file",
            pa.array([f"{month}.parquet"] * n_rows, type=pa.string()),
        )
        month_table = month_table.append_column(
            "_source_system",
            pa.array(["health"] * n_rows, type=pa.string()),
        )

        # Write to raw as YYYY-MM.parquet
        output_path = f"{raw_path}/{month}.parquet"
        with s3.open(output_path, "wb") as f:
            pq.write_table(month_table, f)

        total_rows += n_rows
        print(f"  {month}.parquet: {n_rows:,} rows -> {output_path}")

    # Clean up old-format files (non YYYY-MM.parquet) from raw
    try:
        all_raw_files = s3.glob(f"{raw_path}/*.parquet")
        for f in all_raw_files:
            filename = f.split("/")[-1]
            if not re.match(r"^\d{4}-\d{2}\.parquet$", filename):
                print(f"  Removing old-format file: {filename}")
                s3.rm(f)
    except Exception:
        pass

    return total_rows


def run_pipeline(source_systems: list[str] | None = None):
    """
    Run the cleanse pipeline for specified source systems.

    Args:
        source_systems: List of source systems to process (default: all)
    """
    bucket = get_bucket()
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

        if source == "health":
            # Health uses monthly partitioned output
            print("\n  Processing: health_metrics (monthly partitioned)")
            rows = cleanse_health_monthly(s3, bucket)
            total_rows += rows
        else:
            # All other sources use standard 1:1 file copy
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
