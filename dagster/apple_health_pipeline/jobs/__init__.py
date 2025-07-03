"""Job definitions and schedules for the Apple Health pipeline."""

from dagster import (
    AssetSelection,
    DefaultScheduleStatus,
    RunRequest,
    define_asset_job,
    schedule,
)

# Define the main pipeline job
apple_health_pipeline_job = define_asset_job(
    name="apple_health_pipeline_job",
    description="Process Apple Health data: ingest, transform, and generate calendar",
    selection=AssetSelection.all(),
    tags={
        "pipeline": "apple-health",
        "team": "data",
    },
)


# Daily schedule matching the GitHub Actions cron
@schedule(
    cron_schedule="0 13 * * *",  # Runs every day at midnight AEST
    job=apple_health_pipeline_job,
    default_status=DefaultScheduleStatus.RUNNING,
    execution_timezone="Australia/Melbourne",
)
def daily_pipeline_schedule(context):
    """Daily schedule for the Apple Health pipeline."""
    return RunRequest(
        tags={
            "schedule": "daily",
            "triggered_by": "schedule",
        }
    )


# You can also create separate jobs for different parts of the pipeline
ingestion_job = define_asset_job(
    name="ingestion_job",
    description="Ingest data from Hevy and OpenPowerlifting",
    selection=AssetSelection.groups("ingestion"),
    tags={
        "pipeline": "apple-health",
        "stage": "ingestion",
    },
)

transformation_job = define_asset_job(
    name="transformation_job",
    description="Run dbt transformations",
    selection=AssetSelection.all() - AssetSelection.groups("ingestion", "calendar"),
    tags={
        "pipeline": "apple-health",
        "stage": "transformation",
    },
)

calendar_job = define_asset_job(
    name="calendar_job",
    description="Generate and upload calendar",
    selection=AssetSelection.groups("calendar"),
    tags={
        "pipeline": "apple-health",
        "stage": "output",
    },
)
