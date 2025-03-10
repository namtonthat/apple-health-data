import boto3
from ics import Calendar, Event
import pandas as pd
from typing import List
import logging
import conf

# import json
import yaml
import s3fs
import fastparquet as fp
import urllib
from models import AppleHealthEvent


s3 = boto3.client("s3")
# personal = boto3.Session(profile_name="personal")
# s3 = personal.client("s3")


def collect_event_stats(
    stats_df: pd.DataFrame, column_names: List[str]
) -> pd.DataFrame:
    """
    Extract health data from stats dataframe in the format
    [['name', 'qty']] where:
    - name: name of the health data
    - qty: value (in respective unit) of the health data

    Output:
        - DataFrame of health data in the format [['name', 'qty']]
    """
    filtered_stats = stats_df[stats_df["name"].isin(column_names)]
    event_type_stats = filtered_stats[["name", "qty"]]

    return event_type_stats


def create_day_events(
    stats: pd.DataFrame, event_date: str, object_mapping: dict
) -> List[Event]:
    """
    Iterate through different event types (food / activity / sleep)
    and generate events to add to the daily calendar only if event exists
    """
    day_events = []
    for types, col_names in object_mapping.items():
        logging.info(f"Creating {types} event")
        # collect object name and arguments
        # dynamically create event type objects
        dataclass_name = types.title()
        dataclass_obj = globals()[dataclass_name]
        logging.info("object to create %s", dataclass_obj)

        dataclass_obj_stats = collect_event_stats(
            stats_df=stats, column_names=col_names
        )

        obj_args = dict(dataclass_obj_stats.values)
        logging.info("object args %s", obj_args)
        if obj_args:
            obj = dataclass_obj(**obj_args)
            e = AppleHealthEvent(
                date=event_date, title=obj.title, description=obj.description
            ).event
            day_events.append(e)

    return day_events


def get_latest_health_data(bucket, key):
    """Parse all parquest files and return unique data for all metrics"""
    # Read the parquet file
    s3fileSystem = s3fs.S3FileSystem()
    fs = s3fs.core.S3FileSystem()
    s3_file_path = fs.glob(path=f"{bucket}/{key}")

    fp_obj = fp.ParquetFile(s3_file_path, open_with=s3fileSystem.open)
    df_latest = fp_obj.to_pandas()

    return df_latest


def collect_groups(column_mapping):
    """Collect all groups from column mapping"""
    grouped = {}

    for column, mapping in column_mapping.items():
        group = mapping["group"]

        if group == "sleep_times":
            group = "sleep"

        if group not in grouped:
            grouped[group] = []
        grouped[group].append(column)

    return grouped


def run(event, context):
    """Main handler for lambda event"""
    bucket = event.get("Records")[0].get("s3").get("bucket").get("name")
    key = urllib.parse.unquote_plus(
        event.get("Records")[0].get("s3").get("object").get("key"), encoding="utf-8"
    )

    print("bucket", bucket)
    print("key", key)

    calendar_file_name = conf.calendar_name
    column_mapping = yaml.safe_load(open(conf.column_mapping_file, "r"))
    event_objects_mapping = collect_groups(column_mapping)
    df = get_latest_health_data(bucket, key)

    c = Calendar()
    available_dates = df["date"].unique()

    for date in available_dates:
        daily_stats = df[df["date"] == date]
        daily_calendar = create_day_events(
            stats=daily_stats, event_date=date, object_mapping=event_objects_mapping
        )
        for event in daily_calendar:
            c.events.add(event)

    logging.info("Writing data to calendar ics file")
    s3.put_object(
        Bucket=bucket,
        Key=f"outputs/{calendar_file_name}",
        Body=c.serialize(),
        ACL="public-read",
    )

    # aws_region = "ap-southeast-2"
    bucket_location = boto3.client("s3").get_bucket_location(Bucket=bucket)
    s3_website_url = f"https://{bucket}.s3-{bucket_location}.amazonaws.com/outputs/{calendar_file_name}"
    logging.info("Object now publically available at %s", s3_website_url)

    return
