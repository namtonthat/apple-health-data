import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Optional

import boto3
import polars as pl
import yaml
from dotenv import load_dotenv
from ics import Calendar, Event

load_dotenv()

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

EVENT_FILE_NAME = "event_formats.yaml"

AWS_REGION = os.getenv("AWS_REGION")
CALENDAR_NAME = os.getenv("CALENDAR_NAME", "apple-health-calendar.ics")
S3_BUCKET = os.getenv("S3_BUCKET")


@dataclass
class EventConfig:
    """Configuration for a specific event type"""

    name: str
    title_template: str
    description_template: str
    required_metrics: list[str]

    @classmethod
    def from_yaml(cls, yaml_path: Path, group_name: str) -> "EventConfig":
        """Load configuration from a YAML file for a specific group"""
        with Path.open(yaml_path) as f:
            config = yaml.safe_load(f)

        group_config = config.get("groups", {}).get(group_name, {})
        if not group_config:
            raise ValueError("Group '%s' not found in config" % group_name)

        return cls(
            name=group_name,
            title_template=group_config.get("title", ""),
            description_template=group_config.get("description", ""),
            required_metrics=group_config.get("required_metrics", []),
        )


@dataclass
class ConfigManager:
    """Manages event configurations from YAML"""

    config_path: str
    event_configs: dict[str, EventConfig] = field(default_factory=dict)

    def get_config(self, group_name: str) -> EventConfig:
        """Get configuration for a specific group, loading if needed"""
        if group_name not in self.event_configs:
            self.event_configs[group_name] = EventConfig.from_yaml(
                Path(self.config_path), group_name
            )
        return self.event_configs[group_name]


@dataclass
class DataLoader:
    """Loads data from S3 Parquet files"""

    @staticmethod
    def load_from_s3(s3_bucket: str, s3_path: str) -> pl.DataFrame:
        """Load a Parquet file from S3"""
        s3_uri = f"s3://{s3_bucket}/{s3_path}"
        logging.info("Reading %s", s3_uri)
        return pl.read_parquet(s3_uri)


@dataclass
class EventFactory:
    """Creates calendar events from data and configurations"""

    @staticmethod
    def create_event_for_date(
        event_date: date, df: pl.DataFrame, config: EventConfig
    ) -> Optional[Event]:
        """Create a calendar event for a specific date and event type"""
        # Extract metrics and units separately
        metrics = EventFactory._extract_metrics(df)
        _units = EventFactory._extract_units(df)
        # Rename unit keys to match YAML template (e.g. in_bed_time_unit)
        units = {f"{k}_units": v for k, v in _units.items()}

        # Check if all required metrics are available in either metrics or units
        combined = {**metrics, **units}
        missing_fields = [m for m in config.required_metrics if m not in combined]
        if missing_fields:
            logging.warning(
                "Missing required fields for %s on %s: %s",
                config.name,
                event_date,
                missing_fields,
            )
            return None

        event = Event()

        # Set title using template, including units if available
        try:
            event.name = config.title_template.format(**metrics, **units)
        except KeyError as e:
            logging.warning("Missing metric %s for title template on %s", e, event_date)
            event.name = f"{config.name.capitalize()} Summary for {event_date}"

        # Set description using template
        try:
            event.description = config.description_template.format(**metrics)
        except KeyError as e:
            logging.warning(
                "Missing metric %s for description template on %s", e, event_date
            )
            event.description = f"Data for {event_date}"

        event.begin = datetime.combine(event_date, time(0, 0))
        event.make_all_day()

        return event

    @staticmethod
    def _extract_metrics(df: pl.DataFrame) -> dict[str, float | str]:
        """Extract metrics from DataFrame into a dictionary"""
        metrics: dict[str, float | str] = {}
        rows = df.select(["metric_name", "quantity", "units"]).to_dicts()
        for row in rows:
            name = row["metric_name"]
            try:
                if isinstance(row["quantity"], str):
                    metrics[name] = row["quantity"]
                else:
                    metrics[name] = float(row["quantity"])
            except (ValueError, TypeError):
                metrics[name] = row["quantity"]
        return metrics

    @staticmethod
    def _extract_units(df: pl.DataFrame) -> dict[str, str]:
        """Extract units from DataFrame into a dictionary"""
        units: dict[str, str] = {}
        rows = df.select(["metric_name", "units"]).to_dicts()
        for row in rows:
            name = row["metric_name"]
            if "units" in row and row["units"] is not None:
                try:
                    if isinstance(row["units"], str):
                        units[name] = row["units"]
                    else:
                        units[name] = str(row["units"])
                except (ValueError, TypeError):
                    units[name] = row["units"]
        return units


@dataclass
class CalendarStorage:
    """Handles saving calendars locally and to S3"""

    s3_bucket: Optional[str] = None

    def save_local(self, calendar: Calendar, filename: str) -> str:
        """Save calendar to a local file"""
        ics_content = calendar.serialize()
        file_path = Path(filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with Path.open(file_path, "w") as f:
            f.write(ics_content)
        logging.info("Calendar saved locally to %s", filename)
        return ics_content

    def save_to_s3(
        self, calendar: Calendar, filename: str, ics_content: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload calendar to S3 with public read access

        Returns:
            Public URL to the calendar file, or None on failure.
        """
        if not self.s3_bucket:
            logging.info("No S3 bucket configured, skipping S3 upload")
            return None

        if ics_content is None:
            ics_content = calendar.serialize()

        try:
            s3 = boto3.client("s3")
            s3_key = f"calendar/{Path(filename).name}"
            logging.info("Uploading calendar to s3://%s/%s", self.s3_bucket, s3_key)

            s3.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=ics_content,
                ACL="public-read",
                ContentType="text/calendar",
            )

            if AWS_REGION:
                public_url = (
                    f"https://{self.s3_bucket}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
                )
                logging.info("Calendar publicly available at: %s", public_url)
                return public_url
            else:
                logging.warning(
                    "`AWS_REGION` key is missing from config, cannot build public URL."
                )
        except Exception as e:
            logging.error("Error uploading calendar to S3: %s", e)
        return None


@dataclass
class CalendarGenerator:
    """Coordinates the calendar generation process"""

    config_path: str
    s3_bucket: Optional[str] = None
    calendar: Calendar = field(default_factory=Calendar)
    config_manager: ConfigManager = field(init=False)
    storage: CalendarStorage = field(init=False)

    def __post_init__(self):
        self.config_manager = ConfigManager(self.config_path)
        self.storage = CalendarStorage(self.s3_bucket)

    def add_events_from_s3(self, s3_bucket: str, s3_path: str, group_name: str) -> int:
        """Add events from an S3 Parquet file"""
        events_added = 0
        try:
            df = DataLoader.load_from_s3(s3_bucket, s3_path)
            config = self.config_manager.get_config(group_name)
            dates = sorted(df.select("metric_date").unique().to_series().to_list())
            for d in dates:
                if not isinstance(d, date):
                    d = datetime.strptime(d, "%Y-%m-%d").date()
                date_df = df.filter(pl.col("metric_date") == d)
                event = EventFactory.create_event_for_date(d, date_df, config)
                if event:
                    self.calendar.events.add(event)
                    events_added += 1
            logging.info("Added %s %s events to calendar", events_added, group_name)
        except Exception as e:
            logging.error("Error adding %s events: %s", group_name, e)
        return events_added

    def save_calendar(self, filename: str, save_to_s3: bool = False) -> None:
        """Save the calendar locally and optionally to S3"""
        ics_content = self.storage.save_local(self.calendar, filename)
        if save_to_s3:
            self.storage.save_to_s3(self.calendar, filename, ics_content)


if __name__ == "__main__":
    s3_health_paths = {
        "nutrition": "semantic/macros.parquet",
        "activity": "semantic/activity.parquet",
        "sleep": "semantic/sleeps.parquet",
    }

    generator = CalendarGenerator(EVENT_FILE_NAME, s3_bucket=S3_BUCKET)
    total_events = 0
    for group_name, s3_health_path in s3_health_paths.items():
        total_events += generator.add_events_from_s3(
            S3_BUCKET,
            s3_health_path,
            group_name,
        )

    logging.info("%s calendar events saved", total_events)
    generator.save_calendar(CALENDAR_NAME, save_to_s3=True)
