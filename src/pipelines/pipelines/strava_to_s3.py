"""
Pipeline: Strava API -> S3 Landing Zone (landing/strava/)

Extracts activity data from Strava API to landing zone.

Structure:
  s3://{bucket}/landing/strava/activities/{date}.parquet
"""

import os
import sys
from datetime import date
from pathlib import Path

import dlt
from dlt.destinations import filesystem

# Add src to path for imports - this also loads .env via package __init__
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from pipelines.sources.strava import strava_source


def get_s3_destination(extraction_date: str):
    """
    Configure S3 filesystem destination for landing zone.

    Files land as: landing/strava/{table_name}/{date}.{file_id}.parquet
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


def run_pipeline(extraction_date: str | None = None):
    """
    Run the Strava to S3 landing zone extraction.

    Args:
        extraction_date: Date string (YYYY-MM-DD) for file naming, defaults to today

    Data lands in: s3://{bucket}/landing/strava/
    """
    if extraction_date is None:
        extraction_date = date.today().isoformat()

    bucket = os.environ["S3_BUCKET_NAME"]
    destination_path = f"s3://{bucket}/landing/strava"

    pipeline = dlt.pipeline(
        pipeline_name="strava_to_landing",
        destination=get_s3_destination(extraction_date),
        dataset_name="strava",
        pipelines_dir=os.environ.get("DLT_PIPELINE_DIR", ".dlt_pipelines"),
    )

    source = strava_source(activities=True)

    load_info = pipeline.run(
        source,
        loader_file_format="parquet",
    )

    print("=" * 60)
    print("Strava -> Landing Zone Complete")
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


if __name__ == "__main__":
    run_pipeline()
