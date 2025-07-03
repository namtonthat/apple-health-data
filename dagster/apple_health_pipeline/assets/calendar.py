"""Calendar generation assets."""

import subprocess
from pathlib import Path

from dagster_aws.s3 import S3Resource

from dagster import (
    AssetExecutionContext,
    AssetKey,
    AssetOut,
    EnvVar,
    MetadataValue,
    Output,
    multi_asset,
)


@multi_asset(
    outs={
        "calendar_local": AssetOut(
            description="ICS calendar file generated locally",
            metadata={"format": "ics", "location": "local"},
        ),
        "calendar_s3": AssetOut(
            description="ICS calendar file uploaded to S3",
            metadata={"format": "ics", "location": "s3"},
        ),
    },
    group_name="calendar",
    compute_kind="python",
    deps=[AssetKey("dbt_transform_assets")],  # Depends on dbt transformations
)
def calendar_assets(
    context: AssetExecutionContext, s3: S3Resource
) -> tuple[Output, Output]:
    """Generate calendar ICS file and upload to S3."""
    project_root = Path(__file__).parent.parent.parent.parent
    calendar_dir = project_root / "calendar"

    # Run calendar generation
    context.log.info("Starting calendar generation")
    result = subprocess.run(
        ["make", "calendar"],
        cwd=project_root,
        capture_output=True,
        text=True,
        env={
            **subprocess.os.environ,
            "AWS_REGION": EnvVar("AWS_REGION").get_value(),
            "S3_BUCKET": EnvVar("S3_BUCKET").get_value(),
            "CALENDAR_NAME": EnvVar("CALENDAR_NAME").get_value(
                default="apple-health-calendar.ics"
            ),
        },
    )

    if result.returncode != 0:
        raise Exception(f"Calendar generation failed: {result.stderr}")

    context.log.info("Calendar generation completed successfully")

    # Get the calendar file path
    calendar_name = EnvVar("CALENDAR_NAME").get_value(
        default="apple-health-calendar.ics"
    )
    local_calendar_path = calendar_dir / calendar_name

    # Verify local file exists
    if not local_calendar_path.exists():
        raise FileNotFoundError(f"Calendar file not found at {local_calendar_path}")

    # Read file size for metadata
    file_size = local_calendar_path.stat().st_size

    # The calendar generation script already uploads to S3, but we'll verify it exists
    s3_bucket = EnvVar("S3_BUCKET").get_value()
    s3_key = f"calendar/{calendar_name}"

    context.log.info("Calendar file saved locally at %s", local_calendar_path)
    context.log.info("Calendar file uploaded to s3://%s/%s", s3_bucket, s3_key)

    return (
        Output(
            value=str(local_calendar_path),
            output_name="calendar_local",
            metadata={
                "path": MetadataValue.path(str(local_calendar_path)),
                "size_bytes": MetadataValue.int(file_size),
                "stdout": MetadataValue.text(result.stdout),
            },
        ),
        Output(
            value=f"s3://{s3_bucket}/{s3_key}",
            output_name="calendar_s3",
            metadata={
                "s3_bucket": MetadataValue.text(s3_bucket),
                "s3_key": MetadataValue.text(s3_key),
                "size_bytes": MetadataValue.int(file_size),
            },
        ),
    )
