import boto3
from ics import Calendar, Event
import pandas as pd
from typing import List, Optional, List
import logging
from dataclasses import dataclass, field
from datetime import datetime
import io
import tempfile
import os
import s3fs
import fastparquet as fp
import numpy as np
import json
from pydantic import validate_arguments

s3 = boto3.client("s3")
# personal = boto3.Session(profile_name='personal')
# s3 = personal.resource('s3')


@dataclass
class AppleHealthEvent(Event):
    """
    An event derived from Apple Health data
    For usage within .ics format
    """

    date: datetime.date
    description: str
    title: str

    @property
    def event(self):
        all_day_date = f"{self.date} 00:00:00"
        e = Event()
        e.name = self.title
        e.description = self.description
        e.begin = all_day_date
        e.end = all_day_date
        e.make_all_day()

        return e


@validate_arguments
@dataclass
class AppleHealthData:
    """
    A dataclass to hold all the data from Apple Health
    Parsing from AWS API Gateway and S3
    """

    date: str
    date_updated: str
    name: str
    qty: float
    units: str
    source: Optional[str] = None

    def __post_init__(self):
        self.date = datetime.strptime(self.date, "%Y-%m-%d %H:%M:%S %z")
        self.date_updated = datetime.strptime(self.date_updated, "%Y-%m-%d %H:%M:%S.%f")


@validate_arguments
@dataclass
class Time:
    "A basic time object in hours"
    time: Optional[float] = field(default=0)
    timeInMinutes: Optional[float] = field(default=0)

    def __post_init__(self):
        if self.timeInMinutes:
            self.time = self.timeInMinutes / 60

    @property
    def hours(self) -> float:
        hours = int(self.time)
        return hours

    @property
    def minutes(self) -> str:
        minutes = int((self.time - self.hours) * 60)
        return minutes

    @property
    def title(self) -> str:
        title = f"{self.hours}h {self.minutes}m"
        return title


@validate_arguments
@dataclass
class Food:
    "A basic food object"
    carbohydrates: float
    protein: float
    total_fat: float
    fiber: float
    calories_burnt: Optional[float] = field(default=0)

    def __post_init__(self):
        # rename objects for easier usage
        self.carb = self.carbohydrates
        self.fat = self.total_fat
        self.calories_burnt = round(self.calories_burnt / 4, 2)

    @property
    def calories_ate(self) -> float:
        calories = (self.carb + self.protein) * 4 + (self.fat) * 9
        return calories

    @property
    def macros(self) -> str:
        return f"{self.carb:.0f}C, {self.protein:.0f}P, {self.fat:.0f}F"

    @property
    def title(self) -> str:
        title = f"🔥 {self.calories_ate:.0f} cals ({self.macros})"
        return title

    @property
    def description(self) -> str:
        description = f"""
        🔥 {self.calories_burnt:.0f} kcal
        🍽️ {self.calories_ate:.0f} kcal
        🥞 {self.macros}
        🍇 {self.fiber:.0f} g
        """
        return description


@dataclass
class Activity:
    "A basic activity for activity and mindfulness"
    apple_exercise_time: float
    mindful_minutes: float = None

    def __post_init__(self):
        # rename objects for easier usage
        self.apple_exercise_time = Time(timeInMinutes=self.apple_exercise_time)
        self.mindful_minutes = Time(timeInMinutes=self.mindful_minutes)

    @property
    def activity_description(self) -> str:
        a_description = f"🚴‍♂️ Activity: {self.apple_exercise_time.title} active"
        return a_description

    @property
    def mindful_description(self) -> str:
        m_description = f"🧘 Mindful: {self.mindful_minutes.title} mindful"
        return m_description

    @property
    def description(self) -> str:
        description = f"""
        {self.activity_description}
        {self.mindful_description}
        """
        return description

    @property
    def mindful_title(self) -> str:
        title = f"🧠 {self.mindful_minutes.minutes} mins "
        return title

    @property
    def activity_title(self) -> str:
        "Create blocks of 1 hour increments of activity minutes"
        block = str(self.apple_exercise_time.hours)
        title = f"🚴‍♂️ {block}"
        return title

    @property
    def title(self) -> str:
        title = f"{self.mindful_title} | {self.activity_title}"
        return title


@dataclass
class Sleep:
    "A basic sleep object"
    asleep: float
    inBed: float
    inBedStartTime: str

    def __post_init__(self):
        # rename objects for easier usage
        self.time_asleep = Time(time=self.asleep)
        self.time_in_bed = Time(self.inBed)
        self.in_bed_time = convert_to_12_hr(self.inBedStartTime)

    @property
    def efficiency(self) -> float:
        efficiency = self.time_asleep.time / self.time_in_bed.time * 100
        return efficiency

    @property
    def efficiency_title(self) -> str:
        efficient = f"{self.efficiency:.0f}%"
        efficiency_title = f"🛏️ {efficient}"
        return efficiency_title

    @property
    def title(self) -> str:
        title = f"💤 {self.time_asleep.title} ({self.in_bed_time})"
        print(title)
        return title

    @property
    def description(self) -> str:
        s_description = f"""
        💤 Time asleep: {self.time_asleep.title}
        🛏️ Time in bed: {self.time_in_bed.title}
        🧮 Efficiency: {self.efficiency_title}
        """
        return s_description


# Functions
def convert_to_12_hr(time_str: str) -> str:
    "Lambda function to convert 24 hour time to 12 hour time"
    time_as_24_hr = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S %z").time()
    time_as_12_hr = time_as_24_hr.strftime("%-I:%M %p")
    return time_as_12_hr


def collect_event_stats(
    stats_df: pd.DataFrame, column_names: List[str]
) -> pd.DataFrame:
    """
    Extract health data from stats dataframe in the format
    [['name', 'qty']] where:
    - name: name of the health data
    - qty: value (in respective unit) of the health data

    Output:
        - DataFrame of health data in the format [['name', 'qty']]
    """
    filtered_stats = stats_df[stats_df["name"].isin(column_names)]
    event_type_stats = filtered_stats[["name", "qty"]]

    return event_type_stats


def create_day_events(
    stats: pd.DataFrame, event_date: str, object_mapping: dict
) -> List[Event]:
    """
    Iterate through different event types (food / activity / sleep)
    and generate events to add to the daily calendar only if event exists
    """
    day_events = []

    for types, col_names in object_mapping.items():
        logging.info(f"Creating {types} event")
        # collect object name and arguments
        # dynamically create event type objects
        dataclass_name = types
        dataclass_obj = globals()[dataclass_name]

        dataclass_obj_stats = collect_event_stats(
            stats_df=stats, column_names=col_names
        )

        obj_args = dict(dataclass_obj_stats.values)

        if obj_args:
            obj = dataclass_obj(**obj_args)
            e = AppleHealthEvent(
                date=event_date, title=obj.title, description=obj.description
            ).event
            day_events.append(e)

    return day_events


def get_latest_health_data(bucket, config_path):
    """Parse all parquest files and return unique data for all metrics"""
    # Read the parquet file
    s3fileSystem = s3fs.S3FileSystem()
    fs = s3fs.core.S3FileSystem()

    bucket_uri = f"{bucket}/parquets/*.parquet"
    all_paths_from_s3 = fs.glob(path=bucket_uri)
    df = pd.DataFrame()
    for s3_file in all_paths_from_s3:
        fp_obj = fp.ParquetFile(s3_file, open_with=s3fileSystem.open)
        # convert to pandas dataframe
        df_s3_file = fp_obj.to_pandas()
        df = pd.concat([df, df_s3_file])

    df["date"] = df["date"].astype("str")
    df["date"] = [f[:10] for f in df["date"]]
    cte_latest_data = df.groupby(["date", "name"]).agg({"date_updated": np.max})
    df_latest = df.merge(
        cte_latest_data, on=["date", "name", "date_updated"], how="inner"
    )

    return df_latest


def run(event, context):
    """Main handler for lambda event"""
    bucket = event.get("Records")[0].get("s3").get("bucket").get("name")
    config_path = os.environ["LAMBDA_TASK_ROOT"] + "/config"
    calendar_file_name = "apple-health-calendar.ics"
    event_objects_mapping = json.loads(open(f"{config_path}/mapping.json").read())

    df = get_latest_health_data(bucket, config_path)

    logging.info("Writing latest data into a single parquet file")
    with tempfile.NamedTemporaryFile() as tmp:
        df.to_parquet(tmp.name, engine="fastparquet", index=False)
        with open(tmp.name, "rb") as fh:
            parquet_buffer = io.BytesIO(fh.read())

    response = s3.put_object(
        Bucket=bucket,
        Key="latest_data.parquet",
        Body=parquet_buffer.getvalue(),
    )

    c = Calendar()
    available_dates = df["date"].unique()

    for date in available_dates:
        daily_stats = df[df["date"] == date]
        daily_calendar = create_day_events(
            stats=daily_stats, event_date=date, object_mapping=event_objects_mapping
        )
        for event in daily_calendar:
            c.events.add(event)

    logging.info("Writing data to calendar ics file")
    s3.put_object(
        Bucket=bucket, Key=f"calendars/{calendar_file_name}", Body=c.serialize()
    )

    return response
