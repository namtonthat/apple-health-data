"""Apple Health Data Pipeline - Dagster Implementation."""

from pathlib import Path

from dagster_aws.s3 import S3Resource
from dagster_dbt import DbtCliResource

from dagster import Definitions, EnvVar

from .assets.calendar import generate_calendar
from .assets.dbt import apple_health_dbt_assets
from .assets.ingestion import raw_data_sources
from .schedules import schedules

# Path to the dbt project
DBT_PROJECT_DIR = Path(__file__).parent.parent.parent / "transforms"

defs = Definitions(
    assets=[raw_data_sources, apple_health_dbt_assets, generate_calendar],
    schedules=schedules,
    resources={
        "dbt": DbtCliResource(project_dir=DBT_PROJECT_DIR),
        "s3": S3Resource(region_name=EnvVar("AWS_REGION")),
    },
)
