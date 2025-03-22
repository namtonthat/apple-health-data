import logging
from pathlib import Path

import boto3
import conf
from botocore.exceptions import NoCredentialsError

logger = logging.getLogger(__name__)


def read_last_processed_date(file_name: str) -> str:
    file_path: Path = Path(file_name)
    if file_path.exists():
        return file_path.read_text().strip()
    else:
        logger.info(
            "No last processed date found. Using default: %s", conf.start_ingest_date
        )
        return conf.start_ingest_date


def write_last_processed_date(file_name: str, date_str: str) -> None:
    file_path: Path = Path(file_name)
    file_path.write_text(date_str)


def upload_to_s3(data: str, bucket: str, key: str) -> None:
    s3 = boto3.client("s3", region_name=conf.aws_region)
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=data)
        logger.info("Successfully uploaded data to s3://%s/%s", bucket, key)
    except NoCredentialsError:
        logger.error("AWS credentials not available.")
