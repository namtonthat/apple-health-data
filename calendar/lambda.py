import polars as pl
import yaml
from ics import Calendar, Event
from datetime import datetime, time
from dataclasses import dataclass
from typing import Optional
import conf
import logging

# Global
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
        """
        Load configuration from a YAML file for a specific group

        Args:
            yaml_path: Path to YAML configuration file
            group_name: Name of the group to load

        Returns:
            EventConfig: Configuration for the specified group
        """
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


class UnifiedCalendarGenerator:
    """
    Class to generate a unified calendar with multiple event types
    """

    def __init__(self, config_path: str):
        """
        Initialize with configuration path

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self.calendar = Calendar()
        self.event_configs = {}  # Store configs by name

    def load_config(self, group_name: str) -> EventConfig:
        """
        Load configuration for a specific group

        Args:
            group_name: Name of the event group to use

        Returns:
            EventConfig: Configuration for the specified group
        """
        if group_name not in self.event_configs:
            self.event_configs[group_name] = EventConfig.from_yaml(
                self.config_path, group_name
            )
        return self.event_configs[group_name]

    def add_events_from_s3(self, s3_bucket: str, s3_path: str, group_name: str) -> None:
        """
        Add events from a parquet file in S3

        Args:
            s3_bucket: S3 bucket name
            s3_path: Path to parquet file within the bucket
            group_name: Name of the event group to use
        """
        # Load data using Polars
        s3_uri = f"s3://{s3_bucket}/{s3_path}"
        print(f"Reading {s3_uri}")
        df = pl.read_parquet(s3_uri)

        # Add events
        self.add_events(df, group_name)

    def add_events(self, df: pl.DataFrame, group_name: str) -> None:
        """
        Add events of a specific type to the calendar

        Args:
            df: Polars DataFrame with columns [metric_date, metric_name, units, quantity]
            group_name: Name of the event group to use
        """
        # Load configuration for this group
        config = self.load_config(group_name)

        # Get unique dates
        dates = df.select("metric_date").unique().to_series().to_list()

        # Process each date
        for date in dates:
            # Create event for this date
            date_df = df.filter(pl.col("metric_date") == date)
            event = self._create_event_for_date(date, date_df, config)

            # If event was created successfully, add to calendar
            if event:
                self.calendar.events.add(event)

    def _create_event_for_date(
        self,
        date: str,
        df: pl.DataFrame,
        config: EventConfig,
    ) -> Optional[Event]:
        """
        Create a calendar event for a specific date and event type

        Args:
            date: Date string in YYYY-MM-DD format
            df: DataFrame filtered for this date
            config: Event configuration

        Returns:
            Event: Calendar event, or None if required metrics are missing
        """
        # Extract metrics from DataFrame
        metrics = self._extract_metrics(df)

        # Check if all required metrics are available
        missing_metrics = [m for m in config.required_metrics if m not in metrics]
        if missing_metrics:
            # Some required metrics are missing
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
            # Handle missing metrics in title template
            print(f"Warning: Missing metric {e} for title template on {date}")
            event.name = f"{config.name.capitalize()} Summary for {date}"

        # Set description using template
        try:
            event.description = config.description_template.format(**metrics)
        except KeyError as e:
            # Handle missing metrics in description template
            print(f"Warning: Missing metric {e} for description template on {date}")
            event.description = f"Data for {date}"

        # Set date
        event.begin = datetime.combine(date, time(0, 0))
        event.make_all_day()

        return event

    def _extract_metrics(self, df: pl.DataFrame) -> dict[str, float]:
        """
        Extract metrics from DataFrame into a dictionary

        Args:
            df: DataFrame filtered for a specific date

        Returns:
            dict: Dictionary mapping metric names to values
        """
        metrics = {}

        # Convert to Python dict
        rows = df.select(["metric_name", "quantity"]).to_dicts()
        for row in rows:
            metric_name = row["metric_name"]
            metrics[metric_name] = row["quantity"]

        return metrics

    def save_calendar(self, filename: str) -> None:
        """
        Save the calendar to an ICS file

        Args:
            filename: Output filename
        """
        with open(filename, "w") as f:
            f.write(str(self.calendar))


if __name__ == "__main__":
    # S3 bucket and paths
    s3_paths = {
        "nutrition": "semantic/macros.parquet",
        "activity": "semantic/activity.parquet",
        # "sleep": "semantic/sleep.parquet",
    }

    # Create unified calendar generator
    calendar_generator = UnifiedCalendarGenerator(EVENT_FILE_NAME)

    # Add events from each S3 parquet file
    for group_name, s3_path in s3_paths.items():
        calendar_generator.add_events_from_s3(conf.s3_bucket, s3_path, group_name)

    # Save the unified calendar
    calendar_generator.save_calendar(conf.calendar_name)

    logging.info(
        f"Generated unified calendar with {len(calendar_generator.calendar.events)} events"
    )
