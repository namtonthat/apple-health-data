import logging
import os
import re
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

load_dotenv()

HEVY_API_KEY: str = os.getenv("HEVY_API_KEY", "default_api_key")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")

# Global variable
S3_KEY_PREFIX = "exercise/"
default_start = (datetime.now() - timedelta(days=365)).isoformat()
START_INGEST_DATE = os.getenv("START_INGEST_DATE", default_start)

logger = logging.getLogger(__name__)


def upload_to_s3(data: str, bucket: str, key: str) -> None:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=data)
        logger.info("Successfully uploaded data to s3://%s/%s", bucket, key)
    except NoCredentialsError:
        logger.error("AWS credentials not available.")


def extract_datetimes_from_s3() -> list[datetime]:
    """
    Lists JSON files in the S3 bucket under the configured prefix and extracts datetime objects
    from file names that follow the pattern:
        {S3_KEY_PREFIX}{datetime_string}.json
    where datetime_string is the output of str(datetime.now()).
    Returns a list of datetime objects found.
    """
    s3 = boto3.client("s3", region_name=AWS_REGION)
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=S3_KEY_PREFIX)
    except Exception as e:
        logger.error("Failed to list objects in S3: %s", e)
        return []

    if "Contents" not in response:
        logger.info("No objects found in S3 under prefix %s.", S3_KEY_PREFIX)
        return []

    # Pattern: capture everything between the prefix and '.json'
    pattern = re.compile(rf"{re.escape(S3_KEY_PREFIX)}(.+)\.json")
    dates: list[datetime] = []
    for obj in response["Contents"]:
        key = obj.get("Key", "")
        match = pattern.match(key)
        if match:
            date_str = match.group(1)
            try:
                dt = datetime.fromisoformat(date_str)
                dates.append(dt)
            except Exception as e:
                logger.error("Failed to parse datetime from key %s: %s", key, e)
    return dates


def get_last_processed_date_from_s3() -> str:
    """
    Uses extract_datetimes_from_s3() to obtain a list of datetime objects,
    then returns the latest datetime as a string (using isoformat with a space separator).
    If no datetime is found, returns start_ingest_date.
    """
    dates: list[datetime] = extract_datetimes_from_s3()
    if dates:
        latest_date = max(dates)
        latest_date_str = latest_date.isoformat(sep=" ")
        logger.info("Latest processed date from S3: %s", latest_date_str)
        return latest_date_str
    else:
        logger.info("No matching JSON files found. Using default date.")
        return START_INGEST_DATE
