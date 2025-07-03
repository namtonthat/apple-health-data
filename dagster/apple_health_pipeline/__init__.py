"""Apple Health Data Pipeline - Dagster Implementation."""

from dagster import Definitions

from .assets.calendar import calendar_assets
from .assets.dbt import dbt_transform_assets
from .assets.ingestion import ingestion_assets
from .jobs import (
    apple_health_pipeline_job,
    calendar_job,
    daily_pipeline_schedule,
    ingestion_job,
    transformation_job,
)
from .resources import get_resource_definitions

# Collect all assets
all_assets = [
    ingestion_assets,
    dbt_transform_assets,
    calendar_assets,
]

# Define the Dagster repository
defs = Definitions(
    assets=all_assets,
    jobs=[
        apple_health_pipeline_job,
        ingestion_job,
        transformation_job,
        calendar_job,
    ],
    schedules=[daily_pipeline_schedule],
    resources=get_resource_definitions(),
)
