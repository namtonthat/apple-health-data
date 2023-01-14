"""Process Apple Health export to create a calendar of events."""

import glob
import os
import pandas as pd
import json
from dataclasses import dataclass, field
from datetime import datetime
from ics import Event, Calendar
from typing import List, Optional
import itertools

import logging

logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

# read configs
with open("config/user_config.json", "r") as f:
    user_config = json.load(f)

analysis_cols = ["qty", "dates", "name", "units"]
RAW_DATA_COLUMNS = user_config.get("raw_data_columns")
EVENT_TYPES = user_config.get("event_types")


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


from typing import Optional


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


@dataclass
class Food:
    "A basic food object"
    carbohydrates: float
    protein: float
    total_fat: float
    fiber: float
    calories_burnt: float

    def __post_init__(self):
        # rename objects for easier usage
        self.carb = self.carbohydrates
        self.fat = self.total_fat

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
    apple_exercise_time: Time
    mindful_minutes: Time = None

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
    asleep: Time
    inBed: Time
    inBedStartTime: str

    def __post_init__(self):
        # rename objects for easier usage
        self.time_asleep = Time(time=self.asleep)
        self.time_in_bed = Time(self.inBed)
        self.in_bed_time = self.inBedStartTime

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


# %%
def create_event(date, event_name, description: None):
    """
    Create an all day event for the given date and type
    :param date: date as type datetime.date
    :param event_name: name of event as string
    """
    all_day_date = f"{date} 00:00:00"
    e = Event()
    e.name = event_name
    e.description = description
    e.begin = all_day_date
    e.end = all_day_date
    e.make_all_day()

    return e


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


def create_day_events(stats: pd.DataFrame, event_date: str) -> List[Event]:
    """
    Iterate through different event types (food / activity / sleep)
    and generate events to add to the daily calendar only if event exists
    """
    day_events = []

    for types, col_names in EVENT_TYPES.items():
        # collect object name and arguments
        # dynamically create event type objects
        dataclass_name = types
        dataclass_obj = globals()[dataclass_name]

        # collect object arguments to initialise objects from stats
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


def convert_kj_to_cal(row, new_name):
    """Converts kj to calories"""
    row_dict = row.to_dict()
    calorie_value = int(row["qty"] / 4)

    # assign new value s
    row_dict["qty"] = calorie_value
    row_dict["name"] = new_name
    row_dict["units"] = "kcal"

    return pd.DataFrame(row_dict, index=[0])


if __name__ == "__main__":
    base_folder = os.getcwd()
    source_folder = base_folder + "/healthlake/"
    apple_health_files = glob.glob(source_folder + "*.json")

    df_raw = pd.DataFrame()

    # collate all json files into one dataframe
    for json_file in apple_health_files:
        json_raw = pd.read_json(json_file, lines=True)
        df_raw = pd.concat([df_raw, json_raw])

    ## write data to outputs/transformations
    df_raw.to_csv("outputs/transformations/raw.csv", index=False)
    LOGGER.info("Raw files saved")

    ## Start of transformations
    df_ahc = df_raw.copy()

    # define transformations to go from df_raw to df_ahc (apple-health-calendar)
    # cleaning values
    df_ahc["dates"] = pd.to_datetime(df_ahc["date"]).dt.date
    df_ahc["qty"] = df_ahc["qty"].fillna(df_ahc["asleep"])

    # create calories
    LOGGER.info("Generating calories columns for %s", df_ahc.shape[0])
    active_energy_rows = df_ahc[df_ahc["name"] == "active_energy"][analysis_cols]

    for _, row in active_energy_rows.iterrows():
        df_row = convert_kj_to_cal(row, "calories_burnt")
        df_ahc = pd.concat([df_ahc, df_row])

    # unpivot sleep columns into its own
    df_sleep = df_ahc[df_ahc["name"].isin(["sleep_analysis"])]
    sleep_data = df_sleep[["asleep", "inBed", "inBedStart", "dates"]].reset_index(
        drop=True
    )

    # convert inBedStart to 12 hour time into new column inBedStartTime
    sleep_data["inBedStartTime"] = sleep_data.apply(
        lambda row: convert_to_12_hr(row["inBedStart"]), axis=1
    )

    # Lambda functions (apply functions by rows)
    df_sleep_data = pd.melt(
        sleep_data, id_vars=["dates"], value_vars=["asleep", "inBed", "inBedStartTime"]
    ).rename(columns={"variable": "name", "value": "qty"})

    # merge back to original data
    df_ahc = pd.concat([df_ahc, df_sleep_data])

    # filter out values
    df_ahc = df_ahc[df_ahc["name"].isin(RAW_DATA_COLUMNS)][analysis_cols].reset_index(
        drop=True
    )

    # CHECKPOINT
    df_ahc.to_csv("outputs/transformations/ahc.csv", index=False)
    LOGGER.info('Transformations completed. Saved to "outputs/transformations/ahc.csv"')

    c = Calendar()
    available_dates = df_ahc["dates"].unique()

    weekly_events = []
    for date in available_dates:
        LOGGER.info("Generating events for %s", date)
        daily_stats = df_ahc[df_ahc["dates"] == date]
        daily_events = create_day_events(stats=daily_stats, event_date=date)
        weekly_events.append(daily_events)

    all_events = list(itertools.chain(*weekly_events))
    ## ADD CHECKPOINT HERE
    LOGGER.info("Adding events into single calendar")
    for event in all_events:
        c.events.add(event)

    with open("outputs/apple_health_calendar.ics", "w") as f:
        f.writelines(c.serialize())
        LOGGER.info("Calendar saved to outputs/apple_health_calendar.ics")
# %%
