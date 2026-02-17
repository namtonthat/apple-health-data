"""
Pipeline: Hevy API -> S3 Landing Zone (landing/hevy/)

Extracts raw workout data from Hevy API to landing zone as Delta tables.
dbt staging models read directly from landing via delta_scan() and handle dedup/typing.

Structure:
  s3://{bucket}/landing/hevy/workouts/          (Delta table)
  s3://{bucket}/landing/hevy/workouts__exercises/          (Delta table)
  s3://{bucket}/landing/hevy/workouts__exercises__sets/     (Delta table)
"""

from pipelines.config import run_s3_pipeline
from pipelines.sources.hevy import hevy_source


def run_pipeline(extraction_date: str | None = None):
    """Run the Hevy to S3 landing zone extraction."""
    return run_s3_pipeline(
        "hevy_to_landing",
        "hevy",
        hevy_source(workouts=True, exercise_templates=False, routines=False),
        extraction_date,
    )


if __name__ == "__main__":
    run_pipeline()
