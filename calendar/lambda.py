import boto3
import duckdb
import polars as pl
import yaml
import logging
import urllib.parse
from typing import Any
from pathlib import Path
from pyarrow.lib import Table
from ics import Calendar, Event
from models import (
    DailysEvent,
    FoodEvent,
    ActivityEvent,
    SleepEvent,
    BaseHealthEventCreator,
)
import conf

# Set up logging
# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)

s3 = boto3.client("s3")

# Globals
COLUMN_MAPPING_FILE = "column-mapping.yaml"

EVENT_CREATORS: dict[str, BaseHealthEventCreator] = {
    "food": FoodEvent,
    "activity": ActivityEvent,
    "sleep": SleepEvent,
    "dailys": DailysEvent,
}


def get_latest_health_data(bucket: str, key: str) -> pl.DataFrame:
    """
    Read a Parquet file from S3 using DuckDB and return a Polars DataFrame.
    """
    s3_path = f"s3://{bucket}/{key}"
    con = duckdb.connect(database=":memory:")
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")
    con.execute("CALL load_aws_credentials();")
    query = f"SELECT * FROM read_parquet('{s3_path}')"
    arrow_table: Table = con.execute(query).arrow()
    return pl.from_arrow(arrow_table)


def collect_event_stats(
    stats_df: pl.DataFrame, column_names: list[str]
) -> pl.DataFrame:
    """
    Select and filter the DataFrame to only include rows with metric_name in column_names.
    Then, return a dictionary containing:
      - 'date': the common date (assumed identical across all filtered rows)
      - 'metrics': a dictionary mapping each metric_name to its quantity.

    This is similar to performing a SELECT date, metric_name, quantity FROM table WHERE metric_name IN (...)
    """
    # Filter the DataFrame for the desired metrics and select the relevant columns.
    filtered: pl.Dataframe = stats_df.filter(
        pl.col("metric_name").is_in(column_names)
    ).select(["metric_date", "metric_name", "quantity"])
    if filtered.is_empty():
        logging.warning("Empty")
        return pl.DataFrame()

    return filtered


class ICSOutputHandler:
    """
    Handles saving an ICS file locally and optionally uploading it to S3.
    """

    def __init__(
        self, calendar_file_name: str, local_dir: Path = Path("outputs")
    ) -> None:
        self.calendar_file_name = calendar_file_name
        self.local_dir = local_dir
        self.local_path = self.local_dir / self.calendar_file_name
        # Ensure the output directory exists
        self.local_dir.mkdir(parents=True, exist_ok=True)
        logging.info("Output directory set to: %s", self.local_dir)

    def write_locally(self, cal: Calendar) -> Path:
        """
        Writes the ICS file to the local outputs directory.
        Returns the Path to the saved file.
        """
        try:
            with self.local_path.open("w", encoding="utf-8") as f:
                f.write(cal.serialize())
            logging.info("ICS file successfully written locally to %s", self.local_path)
        except Exception as e:
            logging.error("Failed to write ICS locally: %s", e)
            raise
        return self.local_path

    def upload_to_s3(self, local_path: Path, bucket: str) -> str:
        """
        Uploads the ICS file from local_path to S3 and returns the public URL.
        """
        try:
            with local_path.open("rb") as f:
                s3.put_object(
                    Bucket=bucket,
                    Key=f"outputs/{self.calendar_file_name}",
                    Body=f.read(),
                    ACL="public-read",
                    ContentType="text/calendar",
                )
            logging.info(
                "ICS file uploaded to S3 bucket %s in outputs/%s",
                bucket,
                self.calendar_file_name,
            )
        except Exception as e:
            logging.error("Failed to upload ICS to S3: %s", e)
            raise

        # Retrieve bucket region and construct the S3 URL
        bucket_location = s3.get_bucket_location(Bucket=bucket)
        region = bucket_location.get("LocationConstraint", conf.aws_region)
        s3_url = f"https://{bucket}.s3-{region}.amazonaws.com/outputs/{self.calendar_file_name}"
        logging.info("ICS file now publicly available at %s", s3_url)
        return s3_url


def create_day_events(
    stats: pl.DataFrame, event_date: str, object_mapping: dict[str, list[str]]
) -> list[Event]:
    """
    For each group (e.g. food, activity, sleep), use the associated event creator
    to generate an ICS event for the given event_date if data exists.
    """
    day_events: list[Event] = []
    for group, col_names in object_mapping.items():
        logging.info("Creating %s event", group)
        stats_df = collect_event_stats(stats_df=stats, column_names=col_names)
        logging.debug("stats_df: %s", stats_df)
        if stats_df.is_empty():
            event_creator = EVENT_CREATORS.get(group)
            if event_creator:
                event = event_creator.create_from_stats(stats_df, event_date)
                day_events.append(event)
            else:
                logging.warning("No event creator defined for group: %s", group)
    return day_events


def collect_groups(column_mapping: dict[str, dict[str, str]]) -> dict[str, list[str]]:
    """
    Build a mapping of groups to their corresponding metric names from the column mapping.
    """
    grouped: dict[str, list[str]] = {}
    for column, mapping in column_mapping.items():
        group = mapping.get("group", "")
        if group == "sleep_times":
            group = "sleep"
        grouped.setdefault(group, []).append(column)
    return grouped


def run(event: dict[str, Any], context: object) -> dict[str, Any]:
    """
    Main Lambda function handler.
    """
    record = event.get("Records", [])[0]
    bucket = record.get("s3", {}).get("bucket", {}).get("name", "")
    key = urllib.parse.unquote_plus(
        record.get("s3", {}).get("object", {}).get("key", ""), encoding="utf-8"
    )
    logging.info("Processing file: s3://%s/%s", bucket, key)

    calendar_file_name = conf.calendar_name
    with open(COLUMN_MAPPING_FILE, "r") as f:
        column_mapping = yaml.safe_load(f)
    event_objects_mapping = collect_groups(column_mapping)

    df = get_latest_health_data(bucket, key)
    unique_dates = df.select(pl.col("metric_date")).unique().to_series().to_list()

    cal = Calendar()
    for event_date in unique_dates:
        daily_stats = df.filter(pl.col("metric_date") == event_date)
        day_events = create_day_events(daily_stats, event_date, event_objects_mapping)
        for ev in day_events:
            cal.events.add(ev)

    output_handler = ICSOutputHandler(calendar_file_name)
    local_file = output_handler.write_locally(cal)

    try:
        if conf.write_to_s3 is True:
            s3_url = output_handler.upload_to_s3(local_file, bucket)
            logging.info("File uploaded to S3 and available at: %s", s3_url)
    except Exception as e:
        logging.error("Error uploading file to S3: %s", e)

    return {"statusCode": 200, "body": "ICS generation completed successfully!"}


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    return run(event, context)


if __name__ == "__main__":
    import json

    # Load a sample event JSON file for local testing
    with open("sample_event.json", "r") as f:
        sample_event = json.load(f)

    class DummyContext:
        function_name = "local_test"
        memory_limit_in_mb = 128
        invoked_function_arn = (
            "arn:aws:lambda:us-east-1:123456789012:function:local_test"
        )
        aws_request_id = "dummy-id"

    dummy_context = DummyContext()
    response = lambda_handler(sample_event, dummy_context)
    print(response)
