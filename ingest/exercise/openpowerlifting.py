"""
openpowerlifting.py

Fetches personal best lifts from an OpenPowerlifting profile URL by scraping the HTML page.

Usage:
    python openpowerlifting.py https://www.openpowerlifting.org/u/namtonthat
"""

import argparse
import json
import logging
import sys
from collections.abc import Iterator
from dataclasses import asdict, dataclass

import requests
from bs4 import BeautifulSoup, Tag

# Configure logging at module load
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class BestLifts:
    """Data class to hold personal best lift stats for a given equipment."""

    equip: str
    squat: float | None = None
    bench: float | None = None
    deadlift: float | None = None
    total: float | None = None
    dots: float | None = None


def get_page_content(url: str) -> str:
    """Fetch HTML content from the given URL, exiting on error."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        logger.error("Error fetching page %s: %s", url, exc)
        sys.exit(1)


def parse_value(text: str) -> float | None:
    """Attempt to convert a string to float, return None on failure."""
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


def build_best_lifts(headers: list[str], rows: list[Tag]) -> Iterator[BestLifts]:
    """Yield BestLifts objects from table headers and row tags."""
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        values = [cell.text.strip() for cell in cells]
        equip = values[0]
        data = {key: None for key in headers}
        for key, val in zip(headers[1:], values[1:]):
            data[key] = parse_value(val)
        yield BestLifts(
            equip=equip,
            squat=data.get("squat"),
            bench=data.get("bench"),
            deadlift=data.get("deadlift"),
            total=data.get("total"),
            dots=data.get("dots"),
        )


def parse_personal_bests(html: str) -> list[BestLifts]:
    """Parse the 'Personal Bests' table from HTML and return BestLifts list."""
    soup = BeautifulSoup(html, "html.parser")
    header = soup.find(
        lambda tag: tag.name in {"h1", "h2", "h3"} and "Personal Bests" in tag.text
    )
    if not header:
        logger.error("Personal Bests section not found in HTML")
        sys.exit(1)

    table = header.find_next("table")
    if not table:
        logger.error("Personal Bests table not found under header")
        sys.exit(1)

    rows = table.find_all("tr")
    headers = [cell.text.strip().lower() for cell in rows[0].find_all(["th", "td"])]

    lifts = list(build_best_lifts(headers, rows))
    logger.info("Parsed %d personal best entries", len(lifts))
    return lifts


def openpowerlifting(url: str) -> list[BestLifts]:
    """
    High-level function to fetch and parse personal bests for a profile URL.

    Returns:
        List of BestLifts instances.
    """
    html = get_page_content(url)
    return parse_personal_bests(html)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch personal best lifts by scraping an OpenPowerlifting profile"
    )
    parser.add_argument(
        "url",
        help="Profile page URL, e.g. https://www.openpowerlifting.org/u/namtonthat",
    )
    args = parser.parse_args()

    best_lifts = openpowerlifting(args.url)
    # Serialize dataclasses to JSON and output
    logger.info(json.dumps([asdict(lift) for lift in best_lifts], indent=2))


if __name__ == "__main__":
    main()
