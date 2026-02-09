"""
Pipeline: Apple Health JSON (S3 landing) -> S3 Landing Zone (landing/health/)

Reads Apple Health JSON exports from landing zone, parses them,
and writes structured parquet files back to landing zone.
Data is then cleansed by the cleanse pipeline before being used by dbt.

Structure:
  Input:  s3://{bucket}/landing/health/*.json
  Output: s3://{bucket}/landing/health/health_metrics/{date}.parquet
"""

from pipelines.config import run_s3_pipeline
from pipelines.sources.apple_health import apple_health_source


def run_pipeline(extraction_date: str | None = None, latest_only: bool = True):
    """Run the Apple Health to S3 landing zone extraction."""
    return run_s3_pipeline(
        "apple_health_to_landing",
        "health",
        apple_health_source(latest_only=latest_only),
        extraction_date,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load Apple Health data to S3")
    parser.add_argument("--date", help="Extraction date (YYYY-MM-DD)", default=None)
    parser.add_argument(
        "--all-files", action="store_true", help="Process all files, not just latest"
    )
    args = parser.parse_args()

    run_pipeline(extraction_date=args.date, latest_only=not args.all_files)
