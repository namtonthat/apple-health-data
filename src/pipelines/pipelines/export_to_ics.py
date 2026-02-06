"""
Pipeline: Export health metrics to ICS calendar format.

Creates subscribable calendar events with daily health summaries:
- Sleep duration and deep sleep
- Macros and calories in format: "2000kcal (165P, 200C, 60F)"

Output: s3://{bucket}/exports/health_metrics.ics
"""

import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid5, NAMESPACE_DNS

# Add src to path and load .env via package __init__
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import pipelines  # noqa: F401, PYR001 - loads .env on import

import duckdb
import s3fs


def get_s3_client() -> s3fs.S3FileSystem:
    """Create S3 filesystem client."""
    return s3fs.S3FileSystem(
        key=os.environ["AWS_ACCESS_KEY_ID"],
        secret=os.environ["AWS_SECRET_ACCESS_KEY"],
        client_kwargs={"region_name": os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-2")},
    )


def get_duckdb_connection() -> duckdb.DuckDBPyConnection:
    """Get DuckDB connection configured for S3 access."""
    conn = duckdb.connect(":memory:")
    conn.execute(f"SET s3_region = '{os.environ.get('AWS_DEFAULT_REGION', 'ap-southeast-2')}'")
    conn.execute(f"SET s3_access_key_id = '{os.environ['AWS_ACCESS_KEY_ID']}'")
    conn.execute(f"SET s3_secret_access_key = '{os.environ['AWS_SECRET_ACCESS_KEY']}'")
    return conn


def format_ics_datetime(dt: date) -> str:
    """Format date as ICS all-day event date (VALUE=DATE format)."""
    return dt.strftime("%Y%m%d")


def generate_uid(event_date: date, event_type: str) -> str:
    """Generate deterministic UID for an event."""
    unique_string = f"{event_date.isoformat()}-{event_type}"
    return str(uuid5(NAMESPACE_DNS, unique_string))


def escape_ics_text(text: str) -> str:
    """Escape special characters for ICS format."""
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def create_ics_event(
    uid: str,
    dtstart: date,
    summary: str,
    description: str = "",
) -> str:
    """Create a single VEVENT block."""
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART;VALUE=DATE:{format_ics_datetime(dtstart)}",
        f"DTEND;VALUE=DATE:{format_ics_datetime(dtstart + timedelta(days=1))}",
        f"SUMMARY:{escape_ics_text(summary)}",
    ]

    if description:
        lines.append(f"DESCRIPTION:{escape_ics_text(description)}")

    lines.append("END:VEVENT")
    return "\r\n".join(lines)


def create_ics_calendar(events: list[str], calendar_name: str = "Health Metrics") -> str:
    """Create complete ICS calendar file."""
    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Apple Health Dashboard//Health Metrics//EN",
        f"X-WR-CALNAME:{calendar_name}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    footer = ["END:VCALENDAR"]

    return "\r\n".join(header) + "\r\n" + "\r\n".join(events) + "\r\n" + "\r\n".join(footer)


def load_daily_summary(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    """Load all daily summary data from S3."""
    bucket = os.environ["S3_BUCKET_NAME"]
    s3_path = f"s3://{bucket}/transformed/fct_daily_summary"

    query = f"""
        SELECT
            date,
            sleep_hours,
            sleep_deep_hours,
            sleep_rem_hours,
            sleep_light_hours,
            protein_g,
            carbs_g,
            fat_g,
            logged_calories,
            calculated_calories,
            weight_kg
        FROM read_parquet('{s3_path}')
        ORDER BY date DESC
    """

    result = conn.execute(query).fetchall()
    columns = ["date", "sleep_hours", "sleep_deep_hours", "sleep_rem_hours",
               "sleep_light_hours", "protein_g", "carbs_g", "fat_g",
               "logged_calories", "calculated_calories", "weight_kg"]

    return [dict(zip(columns, row)) for row in result]


def format_sleep_summary(row: dict) -> str | None:
    """Format sleep data for calendar event."""
    sleep_hours = row.get("sleep_hours")
    if sleep_hours is None:
        return None

    deep = row.get("sleep_deep_hours") or 0
    rem = row.get("sleep_rem_hours") or 0
    light = row.get("sleep_light_hours") or 0

    # Format: "7.5h sleep (1.2h deep)"
    return f"😴 {sleep_hours:.1f}h sleep ({deep:.1f}h deep, {rem:.1f}h REM)"


def format_nutrition_summary(row: dict) -> str | None:
    """Format nutrition data for calendar event."""
    protein = row.get("protein_g")
    carbs = row.get("carbs_g")
    fat = row.get("fat_g")
    calories = row.get("logged_calories")

    # Need at least macros to show nutrition
    if protein is None or carbs is None or fat is None:
        return None

    # Format: "2000kcal (165P, 200C, 60F)"
    if calories:
        return f"🍽️ {int(calories)}kcal ({int(protein)}P, {int(carbs)}C, {int(fat)}F)"
    else:
        return f"🍽️ {int(protein)}P, {int(carbs)}C, {int(fat)}F"


def format_weight_summary(row: dict) -> str | None:
    """Format weight data for calendar event."""
    weight = row.get("weight_kg")
    if weight is None:
        return None
    return f"⚖️ {weight:.1f}kg"


def run_pipeline() -> str:
    """
    Generate ICS calendar file with health metrics (full export).

    Returns:
        S3 path where ICS file was uploaded
    """
    print("=" * 60)
    print("Export Health Metrics to ICS (Full Export)")
    print("=" * 60)

    # Load all data
    conn = get_duckdb_connection()
    daily_data = load_daily_summary(conn)
    print(f"Loaded {len(daily_data)} days of data")

    # Generate events
    events = []
    sleep_count = 0
    nutrition_count = 0
    weight_count = 0

    for row in daily_data:
        event_date = row["date"]
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date[:10])

        # Combine all metrics into a single daily event
        summaries = []
        description_parts = []

        # Sleep
        sleep_summary = format_sleep_summary(row)
        if sleep_summary:
            summaries.append(sleep_summary)
            sleep_count += 1
            if row.get("sleep_light_hours"):
                description_parts.append(f"Light sleep: {row['sleep_light_hours']:.1f}h")

        # Nutrition
        nutrition_summary = format_nutrition_summary(row)
        if nutrition_summary:
            summaries.append(nutrition_summary)
            nutrition_count += 1

        # Weight
        weight_summary = format_weight_summary(row)
        if weight_summary:
            summaries.append(weight_summary)
            weight_count += 1

        # Create event if we have any data
        if summaries:
            event = create_ics_event(
                uid=generate_uid(event_date, "daily-health"),
                dtstart=event_date,
                summary=" | ".join(summaries),
                description="\n".join(description_parts) if description_parts else "",
            )
            events.append(event)

    print(f"Generated {len(events)} calendar events")
    print(f"  - Sleep entries: {sleep_count}")
    print(f"  - Nutrition entries: {nutrition_count}")
    print(f"  - Weight entries: {weight_count}")

    # Create calendar
    ics_content = create_ics_calendar(events, "Health Metrics")

    # Upload to S3
    bucket = os.environ["S3_BUCKET_NAME"]
    s3_path = f"{bucket}/exports/health_metrics.ics"

    s3 = get_s3_client()
    with s3.open(s3_path, "w") as f:
        f.write(ics_content)

    full_path = f"s3://{s3_path}"
    print(f"\nUploaded to: {full_path}")

    # Print sample output
    print("\n" + "=" * 60)
    print("Sample ICS Output (first 3 events):")
    print("=" * 60)
    sample_events = events[:3] if events else []
    for event in sample_events:
        print(event)
        print()

    # Print subscription info
    print("=" * 60)
    print("Calendar Subscription")
    print("=" * 60)
    print(f"""
To subscribe to this calendar:

1. Make the S3 object public or use a presigned URL
2. In your calendar app, add a subscription with the URL:

   https://{bucket}.s3.ap-southeast-2.amazonaws.com/exports/health_metrics.ics

   Or if using CloudFront/custom domain:
   https://your-domain.com/exports/health_metrics.ics

Example event format:
┌────────────────────────────────────────────────────────────┐
│ 😴 7.5h sleep (1.2h deep, 1.8h REM) | 🍽️ 2000kcal (165P, 200C, 60F) | ⚖️ 75.5kg │
└────────────────────────────────────────────────────────────┘
""")

    return full_path


if __name__ == "__main__":
    run_pipeline()
