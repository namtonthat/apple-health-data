"""
dlt source for Apple Health data from S3 landing zone.

Reads JSON files from s3://{bucket}/landing/health/ and flattens
the nested metrics into a normalized structure.
"""

import json
from typing import Iterator

import dlt
import s3fs

from pipelines.config import get_bucket, get_s3_client


def _parse_health_date(date_str: str) -> str:
    """Parse Apple Health date format to ISO date."""
    # Format: "2025-03-12 00:00:00 +1100"
    # Extract just the date part
    return date_str.split(" ")[0]


def _list_health_files(
    s3: s3fs.S3FileSystem, bucket: str, prefix: str = "landing/health"
) -> list[str]:
    """List all health JSON files in S3."""
    path = f"{bucket}/{prefix}"
    files = s3.glob(f"{path}/*.json")
    return sorted(files)


def _read_health_file(s3: s3fs.S3FileSystem, file_path: str) -> dict:
    """Read and parse a health JSON file from S3."""
    with s3.open(file_path, "r") as f:
        return json.load(f)


def _extract_file_timestamp(file_path: str) -> str:
    """Extract timestamp from filename for deduplication."""
    # Filename format: 2025-03-24T04:02:47.040329+00:00.json
    filename = file_path.split("/")[-1].replace(".json", "")
    return filename


@dlt.source(name="apple_health")
def apple_health_source(
    bucket: str | None = None,
    prefix: str = "landing/health",
    latest_only: bool = True,
):
    """
    dlt source for Apple Health data.

    Args:
        bucket: S3 bucket name (defaults to S3_BUCKET_NAME env var)
        prefix: S3 prefix for health files (default: landing/health)
        latest_only: If True, only process the most recent file (default: True)

    Yields:
        health_metrics: Flattened health metrics with date, name, value, units
    """
    if bucket is None:
        bucket = get_bucket()

    return [
        health_metrics_resource(bucket, prefix, latest_only),
    ]


@dlt.resource(
    name="health_metrics",
    write_disposition="merge",
    primary_key=["metric_date", "metric_name", "source"],
)
def health_metrics_resource(
    bucket: str,
    prefix: str = "landing/health",
    latest_only: bool = True,
) -> Iterator[dict]:
    """
    Extract health metrics from Apple Health JSON exports.

    Flattens nested structure into rows with:
    - metric_date: Date of the measurement
    - metric_name: Name of the metric (e.g., step_count, heart_rate)
    - value: The measured value
    - units: Unit of measurement
    - source: Data source (e.g., Apple Watch, iPhone)
    - file_timestamp: Timestamp of the export file (for tracking)
    """
    s3 = get_s3_client()
    files = _list_health_files(s3, bucket, prefix)

    if not files:
        print(f"No health files found in s3://{bucket}/{prefix}/")
        return

    if latest_only:
        # Only process the most recent file
        files = [files[-1]]
        print(f"Processing latest file: {files[0]}")
    else:
        print(f"Processing {len(files)} health files")

    for file_path in files:
        file_timestamp = _extract_file_timestamp(file_path)

        try:
            data = _read_health_file(s3, file_path)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue

        # Navigate to metrics array
        metrics = data.get("data", {}).get("metrics", [])

        for metric in metrics:
            metric_name = metric.get("name")
            units = metric.get("units")
            data_points = metric.get("data", [])

            for point in data_points:
                # Extract date and value
                raw_date = point.get("date")
                if not raw_date:
                    continue

                metric_date = _parse_health_date(raw_date)
                raw_value = point.get("qty")
                value = float(raw_value) if raw_value is not None else None
                source = point.get("source", "Unknown")

                # Handle sleep data which has additional fields
                extra_data = {}
                for key in ["Min", "Max", "Avg", "rem", "deep", "core", "awake", "asleep", "inBed"]:
                    if point.get(key) is not None:
                        extra_data[key.lower()] = point[key]

                yield {
                    "metric_date": metric_date,
                    "metric_name": metric_name,
                    "value": value,
                    "units": units,
                    "source": source,
                    "file_timestamp": file_timestamp,
                    **extra_data,
                }


# Convenience function for direct usage
def get_health_metrics(bucket: str | None = None, latest_only: bool = True) -> Iterator[dict]:
    """Get health metrics directly without dlt pipeline."""
    if bucket is None:
        bucket = get_bucket()
    yield from health_metrics_resource(bucket, latest_only=latest_only)
