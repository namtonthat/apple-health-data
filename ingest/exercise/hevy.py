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

load_dotenv()

# Securely load API key from environment variables
HEVY_API_KEY: str = os.getenv("HEVY_API_KEY", "default_api_key")

# Hevy Related Configuration
BASE_URL: str = "https://api.hevyapp.com/v1"
HEADERS: dict[str, str] = {
    "api-key": HEVY_API_KEY,
    "Accept": "application/json",
}

# Configure logging using deferred interpolation
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

LAST_PROCESSED_FILE: str = "last_processed_date.txt"
MAX_PAGE_SIZE: int = 10
TIMEOUT_LIMIT: float = 10.0

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
    response = await client.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=TIMEOUT_LIMIT,
    )
    response.raise_for_status()
    return response.json()


async def fetch_all_events(
    since: str, page_size: int = MAX_PAGE_SIZE
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        first_page_data: dict[str, Any] = await fetch_workouts_page(
            client, since, 1, page_size
        )
        total_pages: int = first_page_data.get("page_count", 1)
        events: list[dict[str, Any]] = first_page_data.get("events", [])

        tasks = [
            fetch_workouts_page(client, since, page, page_size)
            for page in range(2, total_pages + 1)
        ]
        results = await asyncio.gather(*tasks)
        for result in results:
            events.extend(result.get("events", []))
        return events


# --- Main asynchronous function ---


async def main() -> None:
    last_processed_date: str = utils.read_last_processed_date(LAST_PROCESSED_FILE)
    events: list[dict[str, Any]] = await fetch_all_events(last_processed_date)

    if events:
        for event in events:
            workout = event.get("workout", {})
            logger.debug(
                "Workout ID: %s, Title: %s",
                workout.get("id"),
                workout.get("title"),
            )

        # Update the last processed date based on the latest event's updated_at field.
        # Here, we assume every event contains a workout with an "updated_at" field.
        latest_date: str = max(
            (
                event.get("workout", {}).get("updated_at", "")
                for event in events
                if event.get("workout")
            ),
            default=conf.start_ingest_date,
        )
        utils.write_last_processed_date(LAST_PROCESSED_FILE, latest_date)

        # Convert the events list to JSON (as is) for uploading
        events_data_str: str = json.dumps(events)
        s3_key: str = f"{conf.s3_key_prefix}{datetime.now()}.json"
        utils.upload_to_s3(events_data_str, conf.s3_bucket, s3_key)
    else:
        logger.info("No new workouts found.")


if __name__ == "__main__":
    asyncio.run(main())
