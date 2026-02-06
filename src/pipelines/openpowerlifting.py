"""
OpenPowerlifting Pipeline

Fetches competition results from OpenPowerlifting and saves to S3.
"""

import os
import re
from datetime import datetime

import dlt
import requests
from bs4 import BeautifulSoup

from pipelines.config import get_bucket

OPENPOWERLIFTING_URL = os.environ.get("OPENPOWERLIFTING_URL", "")


def parse_openpowerlifting_page(url: str) -> dict:
    """Parse OpenPowerlifting athlete page and extract competition results."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract athlete name from page title
    title = soup.find("title")
    athlete_name = title.text.split("|")[0].strip() if title else "Unknown"

    # Find the results table
    table = soup.find("table")
    if not table:
        return {"athlete_name": athlete_name, "competitions": [], "personal_bests": {}}

    competitions = []
    headers = []

    # Get headers
    header_row = table.find("tr")
    if header_row:
        headers = [th.text.strip().lower() for th in header_row.find_all(["th", "td"])]

    # Parse data rows
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) >= len(headers):
            comp = {}
            for i, header in enumerate(headers):
                value = cells[i].text.strip()
                # Clean up header names
                key = header.replace(" ", "_").replace(".", "")
                comp[key] = value
            competitions.append(comp)

    # Calculate personal bests
    personal_bests = {
        "squat_kg": 0,
        "bench_kg": 0,
        "deadlift_kg": 0,
        "total_kg": 0,
    }

    for comp in competitions:
        # Try different column name variations
        squat = comp.get("squat", comp.get("best_squat", comp.get("bestsquatkg", "0")))
        bench = comp.get("bench", comp.get("best_bench", comp.get("bestbenchkg", "0")))
        deadlift = comp.get("deadlift", comp.get("best_deadlift", comp.get("bestdeadliftkg", "0")))
        total = comp.get("total", comp.get("totalkg", "0"))

        # Parse numeric values
        try:
            squat_val = float(re.sub(r"[^\d.]", "", str(squat)) or 0)
            bench_val = float(re.sub(r"[^\d.]", "", str(bench)) or 0)
            deadlift_val = float(re.sub(r"[^\d.]", "", str(deadlift)) or 0)
            total_val = float(re.sub(r"[^\d.]", "", str(total)) or 0)

            personal_bests["squat_kg"] = max(personal_bests["squat_kg"], squat_val)
            personal_bests["bench_kg"] = max(personal_bests["bench_kg"], bench_val)
            personal_bests["deadlift_kg"] = max(personal_bests["deadlift_kg"], deadlift_val)
            personal_bests["total_kg"] = max(personal_bests["total_kg"], total_val)
        except (ValueError, TypeError):
            continue

    return {
        "athlete_name": athlete_name,
        "profile_url": url,
        "fetched_at": datetime.now().isoformat(),
        "competitions": competitions,
        "personal_bests": personal_bests,
    }


@dlt.resource(name="personal_bests", write_disposition="replace")
def get_personal_bests():
    """Get personal bests from OpenPowerlifting."""
    if not OPENPOWERLIFTING_URL:
        return

    data = parse_openpowerlifting_page(OPENPOWERLIFTING_URL)

    yield {
        "athlete_name": data["athlete_name"],
        "profile_url": data["profile_url"],
        "fetched_at": data["fetched_at"],
        "squat_kg": data["personal_bests"]["squat_kg"],
        "bench_kg": data["personal_bests"]["bench_kg"],
        "deadlift_kg": data["personal_bests"]["deadlift_kg"],
        "total_kg": data["personal_bests"]["total_kg"],
    }


@dlt.resource(name="competitions", write_disposition="replace")
def get_competitions():
    """Get all competition results from OpenPowerlifting."""
    if not OPENPOWERLIFTING_URL:
        return

    data = parse_openpowerlifting_page(OPENPOWERLIFTING_URL)

    for comp in data["competitions"]:
        comp["athlete_name"] = data["athlete_name"]
        yield comp


def run_pipeline():
    """Run the OpenPowerlifting pipeline."""
    bucket = get_bucket()

    pipeline = dlt.pipeline(
        pipeline_name="openpowerlifting",
        destination=dlt.destinations.filesystem(
            bucket_url=f"s3://{bucket}",
            layout="{table_name}/{load_id}.{file_id}.{ext}",
        ),
        dataset_name="landing/openpowerlifting",
    )

    load_info = pipeline.run([get_personal_bests(), get_competitions()])
    print(f"OpenPowerlifting pipeline completed: {load_info}")
    return load_info


if __name__ == "__main__":
    run_pipeline()
