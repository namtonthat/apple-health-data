"""Ingestion assets for Hevy and OpenPowerlifting data."""

import subprocess
from pathlib import Path

from dagster import (
    AssetExecutionContext,
    AssetOut,
    EnvVar,
    MetadataValue,
    Output,
    multi_asset,
)


@multi_asset(
    outs={
        "hevy_raw_data": AssetOut(
            description="Raw workout data from Hevy API",
            metadata={"format": "json", "destination": "s3"},
        ),
        "openpowerlifting_raw_data": AssetOut(
            description="Competition data from OpenPowerlifting",
            metadata={"format": "csv", "destination": "s3"},
        ),
    },
    group_name="ingestion",
    compute_kind="python",
)
def ingestion_assets(context: AssetExecutionContext) -> tuple[Output, Output]:
    """Ingest data from Hevy and OpenPowerlifting sources."""
    project_root = Path(__file__).parent.parent.parent.parent

    # Run Hevy ingestion
    context.log.info("Starting Hevy data ingestion")
    hevy_result = subprocess.run(
        ["make", "hevy"],
        cwd=project_root,
        capture_output=True,
        text=True,
        env={
            **subprocess.os.environ,
            "AWS_REGION": EnvVar("AWS_REGION").get_value(),
            "HEVY_API_KEY": EnvVar("HEVY_API_KEY").get_value(),
            "S3_BUCKET": EnvVar("S3_BUCKET").get_value(),
        },
    )

    if hevy_result.returncode != 0:
        raise Exception(f"Hevy ingestion failed: {hevy_result.stderr}")

    context.log.info("Hevy data ingestion completed successfully")

    # Run OpenPowerlifting ingestion
    context.log.info("Starting OpenPowerlifting data ingestion")
    opl_result = subprocess.run(
        ["make", "openpowerlifting"],
        cwd=project_root,
        capture_output=True,
        text=True,
        env={
            **subprocess.os.environ,
            "AWS_REGION": EnvVar("AWS_REGION").get_value(),
            "S3_BUCKET": EnvVar("S3_BUCKET").get_value(),
            "OPENPOWERLIFTING_USERNAME": EnvVar(
                "OPENPOWERLIFTING_USERNAME"
            ).get_value(),
        },
    )

    if opl_result.returncode != 0:
        raise Exception(f"OpenPowerlifting ingestion failed: {opl_result.stderr}")

    context.log.info("OpenPowerlifting data ingestion completed successfully")

    return (
        Output(
            value="hevy_data_ingested",
            output_name="hevy_raw_data",
            metadata={
                "stdout": MetadataValue.text(hevy_result.stdout),
                "records_processed": MetadataValue.text("See logs for details"),
            },
        ),
        Output(
            value="openpowerlifting_data_ingested",
            output_name="openpowerlifting_raw_data",
            metadata={
                "stdout": MetadataValue.text(opl_result.stdout),
                "records_processed": MetadataValue.text("See logs for details"),
            },
        ),
    )
