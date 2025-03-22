import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any

import conf
import httpx
import utils
from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

load_dotenv()

# Securely load API key from environment variables
HEVY_API_KEY: str = os.getenv("HEVY_API_KEY", "default_api_key")

# Hevy Related Configuration
BASE_URL: str = "https://api.hevyapp.com/v1"
HEADERS: dict[str, str] = {
    "api-key": HEVY_API_KEY,
    "Accept": "application/json",
}
MAX_PAGE_SIZE: int = 10
TIMEOUT_LIMIT: float = 10.0

# Configure logging using deferred interpolation
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# --- API fetching functions ---

# Tenacity Configuration
RETRY_LIMIT = 3
MIN_WAIT = 4
MAX_WAIT = 10


# Retry configuration
@retry(
    reraise=True,
    stop=stop_after_attempt(RETRY_LIMIT),
    wait=wait_exponential(multiplier=1, min=MIN_WAIT, max=MAX_WAIT),
    retry=retry_if_exception_type(httpx.RequestError),
)
async def _fetch_all_workouts(
    client: httpx.AsyncClient, page: int, page_size: int
) -> dict[str, Any]:
    url: str = f"{BASE_URL}/workouts"
    params: dict[str, Any] = {
        "page": page,
        "pageSize": page_size,
    }
    response = await client.get(url, headers=HEADERS, params=params, timeout=10.0)
    response.raise_for_status()
    return response.json()


async def fetch_all_workouts(page_size: int = MAX_PAGE_SIZE) -> list[dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        first_page_data: dict[str, Any] = await _fetch_all_workouts(
            client, 1, page_size
        )
        total_pages: int = first_page_data.get("page_count", 1)
        events: list[dict[str, Any]] = first_page_data.get("workouts", [])

        tasks = [
            _fetch_all_workouts(client, page, page_size)
            for page in range(2, total_pages + 1)
        ]
        results = await asyncio.gather(*tasks)
        for result in results:
            events.extend(result.get("workouts", []))
        return events


async def _fetch_workouts_since(
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


# Retry configuration
@retry(
    reraise=True,
    stop=stop_after_attempt(RETRY_LIMIT),
    wait=wait_exponential(multiplier=1, min=MIN_WAIT, max=MAX_WAIT),
    retry=retry_if_exception_type(httpx.RequestError),
)
async def fetch_workouts_since(
    since: str, page_size: int = MAX_PAGE_SIZE
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        first_page_data: dict[str, Any] = await _fetch_workouts_since(
            client, since, 1, page_size
        )
        total_pages: int = first_page_data.get("page_count", 1)
        events: list[dict[str, Any]] = first_page_data.get("events", [])

        tasks = [
            _fetch_workouts_since(client, since, page, page_size)
            for page in range(2, total_pages + 1)
        ]
        results = await asyncio.gather(*tasks)
        for result in results:
            events.extend(result.get("events", []))
        return events


# --- Main asynchronous function ---


async def main() -> None:
    last_processed_date: str = utils.get_last_processed_date_from_s3()

    if last_processed_date != conf.start_ingest_date:
        events: list[dict[str, Any]] = await fetch_workouts_since(
            last_processed_date,
            page_size=MAX_PAGE_SIZE,
        )
    else:
        logger.info("No valid last processed date found. Using full workouts endpoint.")
        events: list[dict[str, Any]] = await fetch_all_workouts(page_size=MAX_PAGE_SIZE)

    if events:
        for event in events:
            workout = event.get("workout", {})
            logger.debug(
                "Workout ID: %s, Title: %s",
                workout.get("id"),
                workout.get("title"),
            )

        # Convert the events list to JSON (as is) for uploading
        events_data_str: str = json.dumps(events)
        s3_key: str = f"{conf.s3_key_prefix}{datetime.now().isoformat()}.json"
        utils.upload_to_s3(events_data_str, conf.s3_bucket, s3_key)
        logger.info("Processed %s workouts.", len(events))
    else:
        logger.info("No new workouts found.")


if __name__ == "__main__":
    asyncio.run(main())
