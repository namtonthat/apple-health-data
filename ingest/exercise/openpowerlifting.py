"""
openpowerlifting.py

Fetches all competition lift entries from an OpenPowerlifting profile URL by scraping the HTML page
and saves the results to a Parquet file.

Usage:
    python openpowerlifting.py https://www.openpowerlifting.org/u/namtonthat

Requires:
    pip install requests beautifulsoup4 pandas pyarrow
"""

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Iterator, Optional

import requests
import utils
from bs4 import BeautifulSoup, Tag

# Configure logging at module load
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Environment variables
OPENPOWERLIFTING_URL = os.getenv("OPENPOWERLIFTING_URL")


@dataclass
class CompetitionLift:
    """Data class to hold a single competition lift record."""

    date: str
    meet: str
    equipment: str
    bodyweight_kg: Optional[float]
    weight_class_kg: Optional[float]
    squat1_kg: Optional[float]
    squat2_kg: Optional[float]
    squat3_kg: Optional[float]
    bench1_kg: Optional[float]
    bench2_kg: Optional[float]
    bench3_kg: Optional[float]
    deadlift1_kg: Optional[float]
    deadlift2_kg: Optional[float]
    deadlift3_kg: Optional[float]
    total_kg: Optional[float]
    wilks: Optional[float]


def get_page_content(url: str) -> str:
    """Fetch HTML content from the given URL, exiting on error."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        logger.error("Error fetching page %s: %s", url, exc)
        sys.exit(1)


def parse_value(text: str) -> Optional[float]:
    """Attempt to convert a string to float, return None on failure."""
    txt = text.strip()
    if not txt:
        return None
    try:
        return float(txt)
    except (ValueError, TypeError):
        return None


def build_comp_lifts(headers: list[str], rows: list[Tag]) -> Iterator[CompetitionLift]:
    """Yield CompetitionLift objects from table headers and row tags."""
    # Map header titles to dataclass field names
    key_map = [
        h.lower()
        .replace(" ", "_")
        .replace("(kg)", "_kg")
        .replace("(", "")
        .replace(")", "")
        for h in headers
    ]
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        values = [cell.text.strip() for cell in cells]
        data = dict(zip(key_map, values))
        yield CompetitionLift(
            date=data.get("date", ""),
            meet=data.get("meet", ""),
            equipment=data.get("equipment", ""),
            bodyweight_kg=parse_value(data.get("bodyweight_kg", "")),
            weight_class_kg=parse_value(data.get("weight_class_kg", "")),
            squat1_kg=parse_value(data.get("squat1_kg", "")),
            squat2_kg=parse_value(data.get("squat2_kg", "")),
            squat3_kg=parse_value(data.get("squat3_kg", "")),
            bench1_kg=parse_value(data.get("bench1_kg", "")),
            bench2_kg=parse_value(data.get("bench2_kg", "")),
            bench3_kg=parse_value(data.get("bench3_kg", "")),
            deadlift1_kg=parse_value(data.get("deadlift1_kg", "")),
            deadlift2_kg=parse_value(data.get("deadlift2_kg", "")),
            deadlift3_kg=parse_value(data.get("deadlift3_kg", "")),
            total_kg=parse_value(data.get("total_kg", "")),
            wilks=parse_value(data.get("wilks", "")),
        )


def parse_competition_lifts(html: str) -> list[CompetitionLift]:
    """Parse the 'Competition Results' table from HTML and return CompetitionLift list."""
    soup = BeautifulSoup(html, "html.parser")
    header = soup.find(
        lambda tag: tag.name in {"h1", "h2", "h3"} and "Competition Results" in tag.text
    )
    if not header:
        logger.error("Competition Results section not found in HTML")
        sys.exit(1)

    table = header.find_next("table")
    if not table:
        logger.error("Competition Results table not found under header")
        sys.exit(1)

    rows = table.find_all("tr")
    headers = [cell.text.strip() for cell in rows[0].find_all(["th", "td"])]

    lifts = list(build_comp_lifts(headers, rows))
    logger.info("Parsed %d competition lift entries", len(lifts))
    return lifts


def fetch_competition_lifts(url: str) -> list[CompetitionLift]:
    """
    High-level function to fetch and parse all competition lifts for a profile URL.
    """
    html = get_page_content(url)
    return parse_competition_lifts(html)


if __name__ == "__main__":
    comp_lifts = fetch_competition_lifts(OPENPOWERLIFTING_URL)
    output_data: list[dict] = [asdict(lift) for lift in comp_lifts]
    s3_data = json.dumps(output_data, ensure_ascii=False, indent=2)
    ctrl_load_date = datetime.now().isoformat()

    s3_key_with_filename: str = (
        f"{utils.S3_KEY_PREFIX}openpowerlifting/{ctrl_load_date}.json"
    )
    utils.upload_to_s3(s3_data, utils.S3_BUCKET, s3_key_with_filename)
