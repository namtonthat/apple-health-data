"""
Strava API source for dlt.

Extracts activities from Strava API.
Requires STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, and STRAVA_REFRESH_TOKEN.
"""

import os
from datetime import datetime, timezone
from typing import Iterator

import dlt
import requests

STRAVA_API_BASE = "https://www.strava.com/api/v3"


def get_access_token() -> str:
    """
    Exchange refresh token for access token.

    Strava access tokens expire, so we use the refresh token to get a new one.
    Run scripts/strava-auth.sh to get a valid refresh token.
    """
    client_id = os.environ["STRAVA_CLIENT_ID"]
    client_secret = os.environ["STRAVA_CLIENT_SECRET"]
    refresh_token = os.environ["STRAVA_REFRESH_TOKEN"]

    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def fetch_activities(access_token: str, per_page: int = 100) -> Iterator[dict]:
    """
    Fetch all activities from Strava API with pagination.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    page = 1

    while True:
        response = requests.get(
            f"{STRAVA_API_BASE}/athlete/activities",
            headers=headers,
            params={"page": page, "per_page": per_page},
            timeout=30,
        )
        response.raise_for_status()
        activities = response.json()

        if not activities:
            break

        yield from activities
        page += 1


@dlt.resource(name="activities", write_disposition="replace", primary_key="id")
def strava_activities() -> Iterator[dict]:
    """
    Extract activities from Strava.

    Yields activity records with fields like:
    - id, name, type, sport_type
    - distance, moving_time, elapsed_time
    - total_elevation_gain, elev_high, elev_low
    - start_date, start_date_local, timezone
    - average_speed, max_speed
    - average_heartrate, max_heartrate
    - average_watts, max_watts, weighted_average_watts
    - suffer_score, calories
    """
    print("Fetching Strava access token...")
    access_token = get_access_token()

    print("Fetching activities from Strava...")
    activity_count = 0

    for activity in fetch_activities(access_token):
        activity_count += 1

        # Add extraction metadata
        activity["_extracted_at"] = datetime.now(timezone.utc).isoformat()

        yield activity

    print(f"Fetched {activity_count} activities from Strava")


@dlt.source(name="strava")
def strava_source(
    activities: bool = True,
):
    """
    Strava data source.

    Args:
        activities: Include activities data
    """
    resources = []

    if activities:
        resources.append(strava_activities)

    return resources
