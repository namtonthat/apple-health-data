"""Schedule definitions for the Apple Health pipeline."""

from dagster import (
    AssetSelection,
    DefaultScheduleStatus,
    RunRequest,
    define_asset_job,
    schedule,
)

# Define the main pipeline job that runs all assets
apple_health_pipeline = define_asset_job(
    name="apple_health_pipeline",
    description="Complete Apple Health data pipeline",
    selection=AssetSelection.all(),
)


@schedule(
    cron_schedule="0 13 * * *",  # Runs every day at midnight AEST
    job=apple_health_pipeline,
    default_status=DefaultScheduleStatus.RUNNING,
    execution_timezone="Australia/Melbourne",
)
def apple_health_daily_sync(context):
    """Daily synchronization of Apple Health data."""
    return RunRequest()


# Export schedules list
schedules = [apple_health_daily_sync]
