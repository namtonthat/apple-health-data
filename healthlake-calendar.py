"""Process Apple Health export to create a calendar of events."""

import glob
import os
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime

from ics import Calendar, Event

import logging

logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

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

@dataclass
class HealthStat:
    """
    A health stat derived from Apple Health data
    """
    name: str
    qty: float
    units: str


# Define properties
@dataclass
class Time:
    "A basic time object"
    time: float

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
        if (self.minutes != 0) | (self.hours != 0):
            title = f"{self.hours}h {self.minutes}m"
        else:
            title = ""

        return title


@dataclass
class Food:
    "A basic food object"
    carbohydrates: float
    protein: float
    total_fat: float
    fiber: float


    def __post_init__(self):
        # rename objects for easier usage
        self.carb = self.carbohydrates
        self.fat = self.total_fat

    @property
    def calories(self) -> float:
        calories = (self.carb + self.protein) * 4 + (self.fat) * 9
        return calories

    @property
    def macros(self) -> str:
        return f"{self.carb:.0f}C, {self.protein:.0f}P, {self.fat:.0f}F"

    @property
    def title(self) -> str:
        title = f"🔥 {self.calories:.0f} cals ({self.macros})"
        return title

    @property
    def description(self) -> str:
        description = f"""
        🔥 {self.calories:.0f} kcal
        🥞 {self.macros}
        🍇 {self.fiber:.0f}
        """
        return description

@dataclass
class Sleep:
    "A basic sleep object"
    asleep: Time
    inBed: Time
    inBedStart: str

    def __post_init__(self):
        # rename objects for easier usage
        self.time_asleep = self.asleep
        self.time_in_bed = self.inBed
        self.in_bed_time = self.inBedStart

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
        return title

    @property
    def description(self) -> str:
        description = f"""
        💤 Time asleep: {self.time_asleep.title}
        🛏️ Time in bed: {self.time_in_bed.title}
        🧮 Efficiency: {self.efficiency_title}
        """
        return description


@dataclass
class Activity:
    "A basic activity for activity and mindfulness"
    apple_exercise_time: Time # will almost always have exercise time logged
    mindful_minutes: Time = None # most likely won't have meditation

    def __post_init__(self):
        # rename objects for easier usage
        self.apple_exercise_time = Time(self.apple_exercise_time) if self.apple_exercise_time else Time(0)
        self.mindful_minutes = Time(self.mindful_minutes) if self.mindful_minutes else Time(0)

    @property
    def activity_description(self) -> str:
        a_description = ""
        if self.apple_exercise_time != Time(0):
            a_description = f"🚴‍♂️ Activity: {self.apple_exercise_time.title} active"
        return a_description

    @property
    def mindful_description(self) -> str:
        m_description = ""
        if self.mindful_minutes != Time(0):
            m_description = f"🧘 Mindful: {self.mindful_minutes.minutes} mindful"
        return m_description

    @property
    def mindful_title(self) -> str:
        block = np.floor(self.mindful_minutes.minutes / 10)
        title = f"{block}"
        return title

    @property
    def title(self) -> str:
        title = f"🧠 {self.mindful_title}"
        return title

    @property
    def description(self) -> str:
        description = f"""
        {self.activity_description}
        {self.mindful_description}
        """
        return description


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


def make_description(row, event_type):
    """Create a description field for the event"""

    if event_type in ("sleep", "activity"):
        time = row["qty"]
        hours = int(time)
        minutes = int((time - hours) * 60)

        value = f"{hours} hours {minutes} mins"

    # elif event_type == 'food'

    description = f"{make_event_name(event_type)} {value}"

    return description


def generate_calendar(df):
    """
    Generates a CSV and ICS from the dataframe
    :param df: cleansed dataframe from `create_description_cols`
    :param outputs: as type string - a combination of both the local and public storage
    """

    # output_csv_path = f"{output_path}/{file_name}.csv"
    # calendar_file_name = f'{file_name}.ics'
    file_name = "apple_health"

    csv_file_name = f"{file_name}.csv"
    ics_file_name = f"{file_name}.ics"

    LOGGER.info("Generating calendar (as .ICS)")
    c = Calendar()
    for _, row in df.iterrows():
        e = create_event(row["date"], row["name"], row["dsc"])
        c.events.add(e)

    df.to_csv(csv_file_name, index=False)

    with open(ics_file_name, "w") as f:
        f.write(str(c))
        f.close()

    LOGGER.info("Outputing CSV and ICS to: %s", csv_file_name)
    return



def create_day_calendar(stats: pd.DataFrame, event_date: str):
    """
    Iterate through different event types (food / activity / sleep)
    and generate events to add to the daily calendar only if event exists
    """
    day_calendar = Calendar()
    for types, col_names in EVENT_TYPES.items():

        # collect object name and arguments
        dataclass_name = types.capitalize()
        dataclass_obj = globals()[dataclass_name]
        obj_args = stats[stats['name'].isin(col_names)][['name', 'qty']]
        obj_args = dict(obj_args.values)

        if obj_args:
            obj = dataclass_obj(**obj_args)
            e = AppleHealthEvent(
                date = event_date,
                title = obj.title,
                description = obj.description
            ).event
            day_calendar.events.add(e)


    return day_calendar


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

    names = [
        "carbohydrates",
        "dietary_caffeine",
        "dietary_energy",
        "dietary_sugar",
        "fiber",
        "protein",
        "sleep_analysis",
        "total_fat",
        "weight_body_mass",
    ]

    cols = ["qty", "dates", "name", "units"]
    df_raw = pd.DataFrame()

    for json_file in apple_health_files:
        json_raw = pd.read_json(json_file, lines=True)
        df_raw = pd.concat([df_raw, json_raw])

    ## Start of transformations

    df_ahc = df_raw.copy()

    # define transformations to go from df_raw to df_ahc (apple-health-calendar)
    # cleaning values
    df_ahc["dates"] = pd.to_datetime(df_ahc["date"]).dt.date
    df_ahc["qty"] = df_ahc["qty"].fillna(df_ahc["asleep"])

    # create calories

    active_energy_rows = df_ahc[df_ahc["name"] == "active_energy"][cols]
    dietary_energy_rows = df_ahc[df_ahc["name"] == "dietary_energy"][cols]

    for _, row in active_energy_rows.iterrows():
        df_row = convert_kj_to_cal(row, "calories_burnt")
        df_ahc = pd.concat([df_ahc, df_row])

    for _, row in dietary_energy_rows.iterrows():
        df_row = convert_kj_to_cal(row, "calories_consumed")
        df_ahc = pd.concat([df_ahc, df_row])
    # filter out values
    df_ahc = df_ahc[df_ahc["name"].isin(names)][cols].reset_index(drop=True)

    # round values
    df_ahc["qty"] = df_ahc["qty"].round(2)
