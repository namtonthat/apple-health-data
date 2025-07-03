"""Resource definitions for the Apple Health pipeline."""

import os
from pathlib import Path

from dagster_aws.s3 import S3Resource
from dagster_dbt import DbtCliResource

from dagster import EnvVar


def get_resource_definitions():
    """Get resource definitions for the pipeline."""
    return {
        "s3": S3Resource(
            region_name=EnvVar("AWS_REGION"),
        ),
        "dbt": DbtCliResource(
            project_dir=str(Path(__file__).parent.parent.parent.parent / "transforms"),
            profiles_dir=str(Path(__file__).parent.parent.parent.parent / "transforms"),
            target=os.getenv("DBT_TARGET", "prod"),
        ),
    }
