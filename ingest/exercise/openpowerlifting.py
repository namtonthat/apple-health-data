import logging
import os
import sys
from datetime import datetime
from io import BytesIO

import polars as pl
import requests
import utils
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()
API_URL_TEMPLATE = "https://www.openpowerlifting.org/api/liftercsv/{slug}"


def fetch_lifter_csv(slug: str) -> bytes:
    """Fetch raw CSV data from the OpenPowerlifting lifter API."""
    url = API_URL_TEMPLATE.format(slug=slug)
    logger.info("Fetching data from %s", url)

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to fetch lifter data: %s", exc)
        sys.exit(1)

    return response.content


def process_csv_add_ctrl_load_date(csv_bytes: bytes, ctrl_load_date: str) -> bytes:
    """Read CSV into Polars, add ctrl_load_date column, and serialize back to CSV bytes."""
    # Read CSV from bytes
    df = pl.read_csv(BytesIO(csv_bytes))
    # Add ctrl_load_date column
    df = df.with_columns(pl.lit(ctrl_load_date).alias("ctrl_load_date"))
    # Serialize back to CSV bytes
    return df.write_csv().encode("utf-8")


def main():
    # Get lifter slug from environment
    slug = os.getenv("OPENPOWERLIFTING_USERNAME")
    if not slug:
        logger.error("Environment variable OPENPOWERLIFTING_USERNAME must be set")
        sys.exit(1)

    # Fetch raw CSV
    raw_csv = fetch_lifter_csv(slug)
    # Generate control load date
    ctrl_load_date = datetime.now().isoformat()
    # Process CSV to include ctrl_load_date column
    processed_csv = process_csv_add_ctrl_load_date(raw_csv, ctrl_load_date)

    # Build S3 key
    timestamp = ctrl_load_date.replace(":", "-")
    filename = f"{slug}_{timestamp}.csv"
    prefix = getattr(utils, "S3_KEY_PREFIX", "").rstrip("/")
    key = (
        f"{prefix}/openpowerlifting/{filename}"
        if prefix
        else f"openpowerlifting/{filename}"
    )

    # Upload to S3
    utils.upload_to_s3(processed_csv, utils.S3_BUCKET, key)


if __name__ == "__main__":
    main()
