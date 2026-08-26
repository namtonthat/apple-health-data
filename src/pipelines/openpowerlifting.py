"""
OpenPowerlifting Pipeline

Fetches competition results from the OpenPowerlifting lifter CSV API and saves to S3.
"""

import csv
import io
import os

import dlt
import requests

from pipelines.config import get_bucket

OPENPOWERLIFTING_URL = os.environ.get("OPENPOWERLIFTING_URL", "")


def csv_url_from_profile(profile_url: str) -> str:
    """Derive the lifter CSV API URL from a profile URL (…/u/<username>)."""
    username = profile_url.rstrip("/").rsplit("/", 1)[-1]
    return f"https://www.openpowerlifting.org/api/liftercsv/{username}"


def fetch_lifter_rows(csv_url: str) -> list[dict]:
    """Fetch and parse the lifter CSV; one dict per competition, empty fields as None."""
    response = requests.get(csv_url, timeout=30)
    response.raise_for_status()

    reader = csv.DictReader(io.StringIO(response.text))
    return [{k: (v if v != "" else None) for k, v in row.items()} for row in reader]


@dlt.resource(name="competitions", write_disposition="replace")
def get_competitions(rows: list[dict]):
    """Yield pre-fetched competition rows."""
    yield from rows


def run_pipeline():
    """Run the OpenPowerlifting pipeline."""
    if not OPENPOWERLIFTING_URL:
        print("OPENPOWERLIFTING_URL not set; skipping.")
        return None

    bucket = get_bucket()

    rows = fetch_lifter_rows(csv_url_from_profile(OPENPOWERLIFTING_URL))

    pipeline = dlt.pipeline(
        pipeline_name="openpowerlifting",
        destination=dlt.destinations.filesystem(
            bucket_url=f"s3://{bucket}",
            layout="{table_name}/{load_id}.{file_id}.{ext}",
        ),
        # dlt forbids "/" in dataset names and would normalize "landing/openpowerlifting"
        # to "landing_openpowerlifting" (warning on every internal call). Use the normalized
        # form directly to keep the same S3 output path without the warning spam.
        dataset_name="landing_openpowerlifting",
    )

    # Parquet so dbt staging can read_parquet() straight off the landing prefix.
    load_info = pipeline.run(get_competitions(rows), loader_file_format="parquet")
    print(f"OpenPowerlifting pipeline completed: {load_info}")
    return load_info


if __name__ == "__main__":
    run_pipeline()
