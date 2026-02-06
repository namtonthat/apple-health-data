"""
Pipeline: Apple Health JSON (S3 landing) -> S3 Landing Zone (landing/health/)

Reads Apple Health JSON exports from landing zone, parses them,
and writes structured parquet files back to landing zone.
Data is then cleansed by the cleanse pipeline before being used by dbt.

Structure:
  Input:  s3://{bucket}/landing/health/*.json
  Output: s3://{bucket}/landing/health/health_metrics/{date}.parquet
"""
import os
import sys
from datetime import date
from pathlib import Path

import dlt
from dlt.destinations import filesystem

# Add src to path for imports - this also loads .env via package __init__
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from pipelines.sources.apple_health import apple_health_source


def get_s3_destination(extraction_date: str):
    """
    Configure S3 filesystem destination for landing zone.

    Files land as: landing/health/{table_name}/{date}.{file_id}.parquet
    """
    bucket = os.environ["S3_BUCKET_NAME"]

    return filesystem(
        bucket_url=f"s3://{bucket}/landing",
        credentials={
            "aws_access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
            "aws_secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
            "region_name": os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-2"),
        },
        layout="{table_name}/" + extraction_date + ".{file_id}.{ext}",
    )


def run_pipeline(extraction_date: str | None = None, latest_only: bool = True):
    """
    Run the Apple Health to S3 landing zone extraction.

    Args:
        extraction_date: Date string (YYYY-MM-DD) for file naming, defaults to today
        latest_only: If True, only process the most recent health export (default: True)

    Data lands in: s3://{bucket}/landing/health/health_metrics/{date}.parquet
    """
    if extraction_date is None:
        extraction_date = date.today().isoformat()

    bucket = os.environ["S3_BUCKET_NAME"]
    destination_path = f"s3://{bucket}/landing/health"

    pipeline = dlt.pipeline(
        pipeline_name="apple_health_to_landing",
        destination=get_s3_destination(extraction_date),
        dataset_name="health",
        pipelines_dir=os.environ.get("DLT_PIPELINE_DIR", ".dlt_pipelines"),
    )

    source = apple_health_source(latest_only=latest_only)

    load_info = pipeline.run(
        source,
        loader_file_format="parquet",
    )

    print("=" * 60)
    print("Apple Health -> Landing Zone Complete")
    print("=" * 60)
    print(f"Extraction date: {extraction_date}")
    print(f"Destination: {destination_path}/")
    print(f"Latest only: {latest_only}")
    print(f"\nLoad info: {load_info}")

    if load_info.load_packages:
        print("\nTables loaded:")
        for table in load_info.load_packages[0].schema.tables:
            if not table.startswith("_dlt"):
                print(f"  - {table}/{extraction_date}.parquet")

    return load_info


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load Apple Health data to S3")
    parser.add_argument("--date", help="Extraction date (YYYY-MM-DD)", default=None)
    parser.add_argument("--all-files", action="store_true", help="Process all files, not just latest")
    args = parser.parse_args()

    run_pipeline(extraction_date=args.date, latest_only=not args.all_files)
