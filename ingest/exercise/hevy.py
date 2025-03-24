import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any

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

HEVY_API_KEY: str = os.getenv("HEVY_API_KEY", "default_api_key")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")
START_INGEST_DATE = os.getenv("START_INGEST_DATE")


# Hevy Related Configuration
BASE_URL: str = "https://api.hevyapp.com/v1"
HEADERS: dict[str, str] = {
    "api-key": HEVY_API_KEY,
    "Accept": "application/json",
}
TIMEOUT_LIMIT: float = 10.0

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# --- API fetching functions ---

# Tenacity Configuration
RETRY_LIMIT = 3
MIN_WAIT = 4
MAX_WAIT = 10


@retry(
    reraise=True,
    stop=stop_after_attempt(RETRY_LIMIT),
    wait=wait_exponential(multiplier=1, min=MIN_WAIT, max=MAX_WAIT),
    retry=retry_if_exception_type(httpx.RequestError),
)
async def _fetch_workouts_generic(
    client: httpx.AsyncClient, endpoint: str, params: dict[str, Any]
) -> dict[str, Any]:
    url: str = f"{BASE_URL}/{endpoint}"
    response = await client.get(url, headers=HEADERS, params=params, timeout=10.0)
    response.raise_for_status()
    return response.json()


async def fetch_workouts(
    config: utils.WorkoutFetchConfig,
) -> list[dict[str, Any]]:
    """
    Fetch workouts based on last_processed_date.
    """
    async with httpx.AsyncClient() as client:
        # Fetch the first page to get page_count and initial events.
        logger.info("Using the following params for the first fetch: %s", config.params)
        first_page_data: dict[str, Any] = await _fetch_workouts_generic(
            client, config.endpoint, config.params
        )
        total_pages: int = first_page_data.get("page_count", 1)
        logger.info("Total Pages: %s", total_pages)
        events: list[dict[str, Any]] = first_page_data.get(config.response_key, [])

        # Create tasks to fetch remaining pages concurrently.
        tasks = [
            _fetch_workouts_generic(
                client, config.endpoint, {**config.params, "page": page}
            )
            for page in range(2, total_pages + 1)
        ]
        results = await asyncio.gather(*tasks)
        for result in results:
            events.extend(result.get(config.response_key, []))
        return events


# --- Main asynchronous function ---


async def main() -> None:
    # logging.debug(AWS_REGION)
    # logging.debug(S3_BUCKET)
    # logging.debug(utils.S3_KEY_PREFIX)

    last_processed_date: str = utils.get_last_processed_date_from_s3()
    config = utils.get_workout_fetch_config(last_processed_date)
    events = await fetch_workouts(config)

    if events:
        ctrl_load_date = datetime.now().isoformat()
        workouts = []
        for event in events:
            # If event is an "updated" type and has a nested 'workout', use that.
            workout = event["workout"] if config.incremental else event

            # Append the processed date as a property
            workout["ctrl_load_date"] = ctrl_load_date

            logger.debug(
                "Workout ID: %s, Title: %s",
                workout.get("id"),
                workout.get("title"),
            )
            workouts.append(workout)

        # Convert the events list to JSON (as is) for uploading
        workout_data: str = json.dumps(workouts)
        s3_key_with_filename: str = f"{utils.S3_KEY_PREFIX}{ctrl_load_date}.json"
        utils.upload_to_s3(workout_data, S3_BUCKET, s3_key_with_filename)
        logger.info("Processed %s workouts.", len(events))
    else:
        logger.info("No new workouts found.")


if __name__ == "__main__":
    asyncio.run(main())
