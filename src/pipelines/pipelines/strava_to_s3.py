"""
Pipeline: Strava API -> S3 Landing Zone (landing/strava/)

Extracts activity data from Strava API to landing zone as a Delta table.

Structure:
  s3://{bucket}/landing/strava/activities/      (Delta table)
"""

from pipelines.config import run_s3_pipeline
from pipelines.sources.strava import strava_source


def run_pipeline(extraction_date: str | None = None):
    """Run the Strava to S3 landing zone extraction."""
    return run_s3_pipeline(
        "strava_to_landing",
        "strava",
        strava_source(activities=True),
        extraction_date,
    )


if __name__ == "__main__":
    run_pipeline()
