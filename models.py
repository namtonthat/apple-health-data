"""
Datamodels used in the project
"""
from pydantic import validate_arguments
from dataclasses import dataclass, field
from typing import Optional
from ics import Event
from datetime import datetime


# Functions
def convert_to_12_hr(time_str: str) -> str:
    "Lambda function to convert 24 hour time to 12 hour time"
    time_as_24_hr = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S %z").time()
    time_as_12_hr = time_as_24_hr.strftime("%-I:%M %p")
    return time_as_12_hr


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
class Macros:
    "A basic food object"
    carbohydrates: Optional[float] = field(default=0)
    protein: Optional[float] = field(default=0)
    total_fat: Optional[float] = field(default=0)
    fiber: Optional[float] = field(default=0)
    active_energy: Optional[float] = field(default=0)

    def __post_init__(self):
        # rename objects for easier usage
        self.carb = self.carbohydrates
        self.fat = self.total_fat
        self.active_energy = round(self.active_energy / 4, 2)

    @property
    def calories_ate(self) -> float:
        calories = (self.carb + self.protein) * 4 + (self.fat) * 9
        return calories

    @property
    def macros(self) -> str:
        return f"{self.carb:.0f}C, {self.protein:.0f}P, {self.fat:.0f}F"

    @property
    def title(self) -> str:
        title = f"🍽️ {self.calories_ate:.0f} cals ({self.macros})"
        return title

    @property
    def description(self) -> str:
        description = f"""
        🔥 {self.active_energy:.0f} kcal
        🍽️ {self.calories_ate:.0f} kcal
        🥞 {self.macros}
        🍇 {self.fiber:.0f} g
        """
        return description


@dataclass
class Dailys:
    "A basic daily event"
    apple_exercise_time: Optional[float] = field(default=0)
    mindful_minutes: Optional[float] = field(default=0)
    step_count: Optional[float] = field(default=0)
    weight_body_mass: Optional[float] = field(default=0)

    def __post_init__(self):
        # rename objects for easier usage
        self.apple_exercise_time = Time(timeInMinutes=self.apple_exercise_time)
        self.mindful_minutes = Time(timeInMinutes=self.mindful_minutes)
        self.step_count = float(self.step_count)
        self.weight_body_mass = float(self.weight_body_mass)

    @property
    def activity_description(self) -> str:
        a_description = f"🚴‍♂️ Activity: {self.apple_exercise_time.title} active"
        return a_description

    @property
    def mindful_description(self) -> str:
        m_description = f"🧘 Mindful: {self.mindful_minutes.title} mindful"
        return m_description

    @property
    def step_count_description(self) -> str:
        s_description = f"👣 Steps: {self.step_count:.0f} steps"
        return s_description

    @property
    def weight_description(self) -> str:
        w_description = f"⚖️ Weight: {self.weight_body_mass:.0f} lbs"
        return w_description

    @property
    def description(self) -> str:
        description = f"""
        {self.activity_description}
        {self.mindful_description}
        {self.step_count_description}
        {self.weight_description}
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
    def step_count_title(self) -> str:
        title = f"👣 {self.step_count:.0f} steps"
        return title

    @property
    def weight_title(self) -> str:
        title = f"⚖️ {self.weight_body_mass:.1f} kg"
        return title

    @property
    def title(self) -> str:
        title = f"{self.mindful_title} | {self.activity_title} | {self.step_count_title} | {self.weight_title}"
        return title


@dataclass
class Sleep:
    "A basic sleep object"
    sleep_analysis_asleep: Optional[float] = field(default=0)
    sleep_analysis_inBed: Optional[float] = field(default=0)
    sleep_analysis_sleepStart: Optional[str] = field(default="")

    def __post_init__(self):
        # rename objects for easier usage
        self.time_asleep = Time(time=self.sleep_analysis_asleep)
        self.time_in_bed = Time(time=self.sleep_analysis_inBed)
        if self.sleep_analysis_sleepStart != "":
            self.in_bed_time = convert_to_12_hr(self.sleep_analysis_sleepStart)
        else:
            self.in_bed_time = "No data"

    @property
    def efficiency(self) -> float:
        if self.time_in_bed.time != 0:
            efficiency = self.time_asleep.time / self.time_in_bed.time * 100
        else:
            efficiency = 0
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
        s_description = f"""
        💤 Time asleep: {self.time_asleep.title}
        🛏️ Time in bed: {self.time_in_bed.title}
        🧮 Efficiency: {self.efficiency_title}
        """
        return s_description
