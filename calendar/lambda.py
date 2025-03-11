import boto3
import duckdb
import polars as pl
import yaml
import logging
import urllib.parse
from typing import Any
from ics import Calendar, Event
from models import (
    DailysEvent,
    FoodEvent,
    ActivityEvent,
    SleepEvent,
    BaseHealthEventCreator,
)
import conf  # your configuration module

# Set up logging
logging.basicConfig(level=logging.INFO)

s3 = boto3.client("s3")

# Globals
COLUMN_MAPPING_FILE = "column-mapping.yaml"


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
    arrow_table = con.execute(query).arrow()
    return pl.from_arrow(arrow_table)


def collect_event_stats(
    stats_df: pl.DataFrame, column_names: list[str]
) -> dict[str, Any]:
    """
    Select and filter the DataFrame to only include rows with metric_name in column_names.
    Then, return a dictionary containing:
      - 'date': the common date (assumed identical across all filtered rows)
      - 'metrics': a dictionary mapping each metric_name to its quantity.

    This is similar to performing a SELECT date, metric_name, quantity FROM table WHERE metric_name IN (...)
    """
    # Filter the DataFrame for the desired metrics and select the relevant columns.
    filtered = stats_df.filter(pl.col("metric_name").is_in(column_names)).select(
        ["metric_date", "metric_name", "quantity"]
    )
    if filtered.is_empty():
        return {}

    return filtered


# Mapping from group name to the corresponding event creator class
EVENT_CREATORS: dict[str, BaseHealthEventCreator] = {
    "food": FoodEvent,
    "activity": ActivityEvent,
    "sleep": SleepEvent,
    "dailys": DailysEvent,
}


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
        stats_dict = collect_event_stats(stats_df=stats, column_names=col_names)
        logging.info("Object args: %s", stats_dict)
        if stats_dict:
            event_creator = EVENT_CREATORS.get(group)
            if event_creator:
                event = event_creator.create_from_stats(stats_dict, event_date)
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

    logging.info("Writing ICS file to S3")
    s3.put_object(
        Bucket=bucket,
        Key=f"outputs/{calendar_file_name}",
        Body=cal.serialize(),
        ACL="public-read",
        ContentType="text/calendar",
    )

    bucket_location = boto3.client("s3").get_bucket_location(Bucket=bucket)
    region = bucket_location.get("LocationConstraint", conf.aws_region)
    s3_website_url = (
        f"https://{bucket}.s3-{region}.amazonaws.com/outputs/{calendar_file_name}"
    )
    logging.info("ICS file now publicly available at %s", s3_website_url)

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
