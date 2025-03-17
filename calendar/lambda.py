import polars as pl
import yaml
import boto3
from ics import Calendar, Event
from datetime import datetime, time
from dataclasses import dataclass, field
from typing import Optional, Dict
from pathlib import Path
import conf

EVENT_FILE_NAME = "event_formats.yaml"


@dataclass
class EventConfig:
    """Configuration for a specific event type"""

    name: str
    title_template: str
    description_template: str
    required_metrics: list[str]

    @classmethod
    def from_yaml(cls, yaml_path: str, group_name: str) -> "EventConfig":
        """Load configuration from a YAML file for a specific group"""
        with open(yaml_path, "r") as f:
            config = yaml.safe_load(f)

        group_config = config.get("groups", {}).get(group_name, {})
        if not group_config:
            raise ValueError(f"Group '{group_name}' not found in config")

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
    event_configs: Dict[str, EventConfig] = field(default_factory=dict)

    def get_config(self, group_name: str) -> EventConfig:
        """Get configuration for a specific group, loading if needed"""
        if group_name not in self.event_configs:
            self.event_configs[group_name] = EventConfig.from_yaml(
                self.config_path, group_name
            )
        return self.event_configs[group_name]


@dataclass
class DataLoader:
    """Loads data from S3 Parquet files"""

    @staticmethod
    def load_from_s3(s3_bucket: str, s3_path: str) -> pl.DataFrame:
        """Load a Parquet file from S3"""
        s3_uri = f"s3://{s3_bucket}/{s3_path}"
        print(f"Reading {s3_uri}")
        return pl.read_parquet(s3_uri)


@dataclass
class EventFactory:
    """Creates calendar events from data and configurations"""

    @staticmethod
    def create_event_for_date(
        date: str, df: pl.DataFrame, config: EventConfig
    ) -> Optional[Event]:
        """Create a calendar event for a specific date and event type"""
        # Extract metrics from DataFrame
        metrics = EventFactory._extract_metrics(df)

        # Check if all required metrics are available
        missing_metrics = [m for m in config.required_metrics if m not in metrics]
        if missing_metrics:
            print(
                f"Warning: Missing required metrics for {config.name} on {date}: {missing_metrics}"
            )
            return None

        # Create event
        event = Event()

        # Set title using template
        try:
            event.name = config.title_template.format(**metrics)
        except KeyError as e:
            print(f"Warning: Missing metric {e} for title template on {date}")
            event.name = f"{config.name.capitalize()} Summary for {date}"

        # Set description using template
        try:
            event.description = config.description_template.format(**metrics)
        except KeyError as e:
            print(f"Warning: Missing metric {e} for description template on {date}")
            event.description = f"Data for {date}"

        # Set date
        event.begin = datetime.combine(date, time(0, 0))
        event.make_all_day()

        return event

    @staticmethod
    def _extract_metrics(df: pl.DataFrame) -> dict[str, float]:
        """Extract metrics from DataFrame into a dictionary"""
        metrics = {}

        # Convert to Python dict
        rows = df.select(["metric_name", "quantity"]).to_dicts()
        for row in rows:
            metric_name = row["metric_name"]
            # Try to convert to float for proper formatting
            try:
                # If the quantity is already a string with formatting, keep it as is
                if isinstance(row["quantity"], str) and any(
                    c in row["quantity"] for c in ["%", "AM", "PM"]
                ):
                    metrics[metric_name] = row["quantity"]
                else:
                    # Otherwise, convert to float for numeric formatting
                    metrics[metric_name] = float(row["quantity"])
            except (ValueError, TypeError):
                # If conversion fails, keep the original value
                metrics[metric_name] = row["quantity"]

        return metrics


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

        with open(file_path, "w") as f:
            f.write(ics_content)

        print(f"Calendar saved locally to {filename}")
        return ics_content

    def save_to_s3(
        self,
        calendar: Calendar,
        filename: str,
        ics_content: str = None,
    ) -> str:
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
            print("No S3 bucket configured, skipping S3 upload")
            return None

        # Generate ICS content if not provided
        if ics_content is None:
            ics_content = calendar.serialize()

        try:
            s3 = boto3.client("s3")
            s3_key = f"calendar/{Path(filename).name}"

            print(f"Uploading calendar to s3://{self.s3_bucket}/{s3_key}")

            # Upload with public-read ACL
            s3.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=ics_content,
                ACL="public-read",  # Set public read access
                ContentType="text/calendar",  # Set correct content type for .ics files
            )

            # Generate the public URL
            public_url = f"https://{self.s3_bucket}.s3.amazonaws.com/{s3_key}"
            print(f"Calendar publicly available at: {public_url}")

            return public_url
        except Exception as e:
            print(f"Error uploading calendar to S3: {e}")
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

    def add_events_from_s3(self, s3_bucket: str, s3_path: str, group_name: str) -> None:
        """Add events from an S3 Parquet file"""
        try:
            # Load data
            df = DataLoader.load_from_s3(s3_bucket, s3_path)

            # Get configuration
            config = self.config_manager.get_config(group_name)

            # Get unique dates
            dates = df.select("metric_date").unique().to_series().to_list()

            # Create events for each date
            events_added = 0
            for date in dates:
                # Filter data for this date
                date_df = df.filter(pl.col("metric_date") == date)

                # Create event
                event = EventFactory.create_event_for_date(date, date_df, config)

                # Add to calendar if created successfully
                if event:
                    self.calendar.events.add(event)
                    events_added += 1

            print(f"Added {events_added} {group_name} events to calendar")
        except Exception as e:
            print(f"Error adding {group_name} events: {e}")

    def save_calendar(self, filename: str, save_to_s3: bool = False) -> None:
        """Save the calendar locally and optionally to S3"""
        # Save locally
        ics_content = self.storage.save_local(self.calendar, filename)

        # Save to S3 if requested
        if save_to_s3:
            self.storage.save_to_s3(self.calendar, filename, ics_content)

        print(f"Calendar saved with {len(self.calendar.events)} events")


if __name__ == "__main__":
    s3_bucket = "api-health-data-ntonthat"
    s3_paths = {
        "nutrition": "semantic/macros.parquet",
        "activity": "semantic/activity.parquet",
        "sleep": "semantic/sleeps.parquet",
    }

    # Create calendar generator
    generator = CalendarGenerator(EVENT_FILE_NAME, s3_bucket=conf.s3_bucket)

    # Add events from each S3 parquet file
    for group_name, s3_path in s3_paths.items():
        generator.add_events_from_s3(conf.s3_bucket, s3_path, group_name)

    # Save the calendar locally and to S3
    generator.save_calendar(conf.calendar_name, save_to_s3=True)
