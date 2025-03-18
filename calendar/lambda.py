import logging
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Optional

import boto3
import conf
import polars as pl
import yaml
from ics import Calendar, Event

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

EVENT_FILE_NAME = "event_formats.yaml"


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
        s3_uri = "s3://%s/%s" % (s3_bucket, s3_path)
        logging.info("Reading %s", s3_uri)
        return pl.read_parquet(s3_uri)


@dataclass
class EventFactory:
    """Creates calendar events from data and configurations"""

    @staticmethod
    def create_event_for_date(
        date: datetime, df: pl.DataFrame, config: EventConfig
    ) -> Optional[Event]:
        """Create a calendar event for a specific date and event type"""
        # Extract metrics from DataFrame
        metrics = EventFactory._extract_metrics(df)
        _units = EventFactory._extract_units(df)
        units = {f"{k}_units": v for (k, v) in _units.items()}

        # Check if all required metrics are available
        missing_fields = [
            m for m in config.required_metrics if m not in {**metrics, **units}
        ]
        if missing_fields:
            logging.warning(
                "Missing required fields for %s on %s: %s",
                config.name,
                date,
                missing_fields,
            )
            return None

        # Create event
        event = Event()

        # Set title using template
        try:
            event.name = config.title_template.format(**metrics, **units)
        except KeyError as e:
            logging.warning("Missing metric %s for title template on %s", e, date)
            event.name = "%s Summary for %s" % (config.name.capitalize(), date)

        # Set description using template
        try:
            event.description = config.description_template.format(**metrics)
        except KeyError as e:
            logging.warning("Missing metric %s for description template on %s", e, date)
            event.description = "Data for %s" % date

        # Set date
        event.begin = datetime.combine(date, time(0, 0))
        event.make_all_day()

        return event

    @staticmethod
    def _extract_metrics(df: pl.DataFrame) -> dict[str, float]:
        """Extract metrics from DataFrame into a dictionary"""
        metrics = {}

        # Convert to Python dict
        rows = df.select(["metric_name", "quantity", "units"]).to_dicts()
        for row in rows:
            metric_name = row["metric_name"]
            # Try to convert to float for proper formatting
            try:
                # If the quantity is already a string with formatting, keep it as is
                if isinstance(row["quantity"], str):
                    metrics[metric_name] = row["quantity"]
                else:
                    # Otherwise, convert to float for numeric formatting
                    metrics[metric_name] = float(row["quantity"])
            except (ValueError, TypeError):
                # If conversion fails, keep the original value
                metrics[metric_name] = row["quantity"]

        return metrics

    @staticmethod
    def _extract_units(df: pl.DataFrame) -> dict[str, str]:
        """Extract units from DataFrame into a dictionary"""
        units = {}

        # Convert to Python dict
        rows = df.select(["metric_name", "units"]).to_dicts()
        for row in rows:
            metric_name = row["metric_name"]
            # Try to convert to float for proper formatting
            try:
                units[metric_name] = (
                    row["units"] if isinstance(row["units"], str) else str(row["units"])
                )
            except (ValueError, TypeError):
                # If conversion fails, keep the original value
                units[metric_name] = row["units"]

        return units


@dataclass
class CalendarStorage:
    """Handles saving calendars locally and to S3"""

    s3_bucket: Optional[str] = None

    def save_local(self, calendar: Calendar, filename: str) -> str:
        """Save calendar to a local file"""
        ics_content = calendar.serialize()

        # Create parent directories if they don't exist
        file_path = Path(filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with Path.open(file_path, "w") as f:
            f.write(ics_content)

        logging.info("Calendar saved locally to %s", filename)
        return ics_content

    def save_to_s3(
        self,
        calendar: Calendar,
        filename: str,
        ics_content: Optional[str] = None,
    ) -> Optional[str]:
        """
        Upload calendar to S3 with public read access

        Args:
            calendar: Calendar object to save
            filename: Output filename
            ics_content: Optional pre-generated ICS content

        Returns:
            str: Public URL to the calendar file
        """
        if not self.s3_bucket:
            logging.info("No S3 bucket configured, skipping S3 upload")
            return None

        # Generate ICS content if not provided
        if ics_content is None:
            ics_content = calendar.serialize()

        try:
            s3 = boto3.client("s3")
            s3_key = "calendar/%s" % Path(filename).name

            logging.info("Uploading calendar to s3://%s/%s", self.s3_bucket, s3_key)

            # Upload with public-read ACL
            s3.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=ics_content,
                ACL="public-read",  # Set public read access
                ContentType="text/calendar",  # Set correct content type for .ics files
            )

            # Build the public URL including region if provided
            if conf.aws_region:
                public_url = "https://%s.s3.%s.amazonaws.com/%s" % (
                    self.s3_bucket,
                    conf.aws_region,
                    s3_key,
                )
                logging.info("Calendar publicly available at: %s", public_url)

                return public_url
            else:
                logging.warning(
                    "`aws_region` key is missing from config, cannot build public URL."
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
        try:
            # Load data
            df = DataLoader.load_from_s3(s3_bucket, s3_path)

            # Get configuration
            config = self.config_manager.get_config(group_name)

            # Get unique dates
            dates = sorted(df.select("metric_date").unique().to_series().to_list())

            # Create events for each date
            for date in dates:
                date_df = df.filter(pl.col("metric_date") == date)
                event = EventFactory.create_event_for_date(date, date_df, config)
                if event:
                    self.calendar.events.add(event)

            events_added = len(self.calendar.events)
            logging.info("Added %s %s events to calendar", events_added, group_name)

        except Exception as e:
            logging.error("Error adding %s events: %s", group_name, e)
            events_added = 0
        return events_added

    def save_calendar(self, filename: str, save_to_s3: bool = False) -> None:
        """Save the calendar locally and optionally to S3"""
        # Save locally
        ics_content = self.storage.save_local(self.calendar, filename)

        # Save to S3 if requested
        if save_to_s3:
            self.storage.save_to_s3(self.calendar, filename, ics_content)


if __name__ == "__main__":
    s3_paths = {
        "nutrition": "semantic/macros.parquet",
        "activity": "semantic/activity.parquet",
        "sleep": "semantic/sleeps.parquet",
    }

    # Create calendar generator
    generator = CalendarGenerator(EVENT_FILE_NAME, s3_bucket=conf.s3_bucket)

    # Add events from each S3 parquet file
    total_events = 0
    for group_name, s3_path in s3_paths.items():
        total_events += generator.add_events_from_s3(
            conf.s3_bucket, s3_path, group_name
        )

    logging.info("%s calendar events saved", total_events)
    # Save the calendar locally and to S3
    generator.save_calendar(conf.calendar_name, save_to_s3=True)
