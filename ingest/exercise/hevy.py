import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import boto3
import conf
import httpx
import workout_entities as we  # Import the domain objects and parsing functions
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Securely load API key from environment variables
API_KEY: str = os.getenv("API_KEY", "default_api_key")
BASE_URL: str = "https://api.hevyapp.com/v1"
HEADERS: dict[str, str] = {
    "api-key": API_KEY,
    "Accept": "application/json",
}

# Configure logging using deferred interpolation
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constant for the last processed date file name (as a string)
LAST_PROCESSED_FILE: str = "last_processed_date.txt"

# Define maximum page size as a constant
MAX_PAGE_SIZE: int = 10

# --- File operations: Create Path instances within functions ---


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


# --- API fetching functions ---


async def fetch_workouts_page(
    client: httpx.AsyncClient, since: str, page: int, page_size: int
) -> dict[str, Any]:
    url: str = f"{BASE_URL}/workouts/events"
    params: dict[str, Any] = {
        "since": since,
        "page": page,
        "pageSize": page_size,
    }
    response = await client.get(url, headers=HEADERS, params=params, timeout=10.0)
    response.raise_for_status()
    return response.json()


async def fetch_all_events(
    since: str, page_size: int = MAX_PAGE_SIZE
) -> list[we.Event]:
    async with httpx.AsyncClient() as client:
        first_page_data: dict[str, Any] = await fetch_workouts_page(
            client, since, 1, page_size
        )
        total_pages: int = first_page_data.get("page_count", 1)
        events_raw: list[dict[str, Any]] = first_page_data.get("events", [])
        events: list[we.Event] = [we.parse_event(event) for event in events_raw]

        tasks = [
            fetch_workouts_page(client, since, page, page_size)
            for page in range(2, total_pages + 1)
        ]
        results = await asyncio.gather(*tasks)
        for result in results:
            events_raw = result.get("events", [])
            events.extend([we.parse_event(event) for event in events_raw])
        return events


# --- AWS S3 Upload function ---


def upload_to_s3(data: str, bucket: str, key: str) -> None:
    s3 = boto3.client("s3", region_name=conf.aws_region)
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=data)
        logger.info("Successfully uploaded data to s3://%s/%s", bucket, key)
    except NoCredentialsError:
        logger.error("AWS credentials not available.")


# --- Main asynchronous function ---


async def main() -> None:
    last_processed_date: str = read_last_processed_date(LAST_PROCESSED_FILE)
    events: list[we.Event] = await fetch_all_events(last_processed_date)

    if events:
        for event in events:
            logger.info(
                "Workout ID: %s, Title: %s", event.workout.id, event.workout.title
            )
        latest_date: str = max(event.workout.updated_at for event in events)
        write_last_processed_date(LAST_PROCESSED_FILE, latest_date)

        workouts_data_str: str = json.dumps(
            [event.__dict__ for event in events], default=lambda o: o.__dict__
        )
        s3_key: str = (
            f"{conf.s3_key_prefix}{datetime.now().strftime('%Y-%m-%d')}_workouts.json"
        )
        upload_to_s3(workouts_data_str, conf.s3_bucket, s3_key)
    else:
        logger.info("No new workouts found.")


if __name__ == "__main__":
    asyncio.run(main())
