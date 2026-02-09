"""
Pipeline: Export health metrics to ICS calendar format.

Creates subscribable calendar events with daily health summaries:
- Sleep duration and deep sleep
- Macros and calories in format: "2000kcal (165P, 200C, 60F)"

Output: s3://{bucket}/exports/health_metrics.ics
"""

from datetime import date, datetime, timedelta, timezone
from uuid import NAMESPACE_DNS, uuid5

import duckdb

from pipelines.config import (
    get_bucket,
    get_duckdb_connection,
    get_region,
    get_s3_client,
)


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
    bucket = get_bucket()
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
            weight_kg,
            steps
        FROM read_parquet('{s3_path}')
        ORDER BY date DESC
    """

    result = conn.execute(query).fetchall()
    columns = ["date", "sleep_hours", "sleep_deep_hours", "sleep_rem_hours",
               "sleep_light_hours", "protein_g", "carbs_g", "fat_g",
               "logged_calories", "calculated_calories", "weight_kg", "steps"]

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


def format_steps_summary(row: dict) -> str | None:
    """Format step count for calendar event."""
    steps = row.get("steps")
    if steps is None:
        return None
    return f"🚶 {int(steps):,} steps"


def format_title(row: dict) -> str | None:
    """Format compact calendar title: sleep, weight, protein."""
    parts = []
    if row.get("sleep_hours") is not None:
        parts.append(f"😴 {row['sleep_hours']:.1f}h")
    if row.get("weight_kg") is not None:
        parts.append(f"⚖️ {row['weight_kg']:.1f}kg")
    if row.get("protein_g") is not None:
        parts.append(f"🍗 {int(row['protein_g'])}P")
    return " · ".join(parts) if parts else None


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

        # Sleep
        sleep_summary = format_sleep_summary(row)
        if sleep_summary:
            summaries.append(sleep_summary)
            sleep_count += 1

        # Nutrition
        nutrition_summary = format_nutrition_summary(row)
        if nutrition_summary:
            summaries.append(nutrition_summary)
            nutrition_count += 1

        # Weight + Steps (combined on one line)
        body_parts = []
        weight_summary = format_weight_summary(row)
        if weight_summary:
            body_parts.append(weight_summary)
            weight_count += 1
        steps_summary = format_steps_summary(row)
        if steps_summary:
            body_parts.append(steps_summary)
        if body_parts:
            summaries.append(" · ".join(body_parts))

        # Create event if we have any data
        if summaries:
            title = format_title(row) or summaries[0]
            event = create_ics_event(
                uid=generate_uid(event_date, "daily-health"),
                dtstart=event_date,
                summary=title,
                description="\n".join(summaries),
            )
            events.append(event)

    print(f"Generated {len(events)} calendar events")
    print(f"  - Sleep: {sleep_count}")
    print(f"  - Nutrition: {nutrition_count}")
    print(f"  - Weight: {weight_count}")

    # Create calendar
    ics_content = create_ics_calendar(events, "Health Metrics")

    # Upload to S3 with public-read ACL
    bucket = get_bucket()
    s3_key = "exports/health_metrics.ics"
    s3_path = f"{bucket}/{s3_key}"
    region = get_region()

    s3 = get_s3_client(s3_additional_kwargs={"ACL": "public-read"})
    with s3.open(s3_path, "w", content_type="text/calendar") as f:
        f.write(ics_content)

    full_path = f"s3://{s3_path}"
    public_url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
    print(f"\nUploaded to: {full_path}")
    print(f"Public URL: {public_url}")

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
Subscribe to this calendar in any calendar app:

   {public_url}

   Or if using CloudFront/custom domain:
   https://your-domain.com/exports/health_metrics.ics

Example event format:
┌────────────────────────────────────────┐
│ 😴 7.5h sleep (1.2h deep, 1.8h REM)   │
│ 🍽️ 2000kcal (165P, 200C, 60F)         │
│ ⚖️ 75.5kg · 🚶 8,432 steps             │
└────────────────────────────────────────┘
""")

    return full_path


if __name__ == "__main__":
    run_pipeline()
