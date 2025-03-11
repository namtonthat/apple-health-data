from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, field_validator
from ics import Event


class TimeUnit(BaseModel):
    """
    A unified representation of time durations.
    Internally stored in minutes.
    """

    minutes: float = 0

    @classmethod
    def from_hours(cls, hours: float) -> "TimeUnit":
        return cls(minutes=hours * 60)

    @property
    def hours(self) -> int:
        """Whole hours."""
        return int(self.minutes // 60)

    @property
    def remaining_minutes(self) -> int:
        """Remaining minutes after whole hours are taken out."""
        return int(self.minutes % 60)

    def __str__(self) -> str:
        return f"{self.hours}h {self.remaining_minutes}m"

    @property
    def title(self) -> str:
        """A human-readable representation (e.g., '1h 30m')."""
        return str(self)

    @property
    def title_minutes_only(self) -> str:
        """Representation using minutes only (e.g., '30m')."""
        return f"{self.remaining_minutes}m"


class EventDescriptionMixIn:
    """
    Mixin that provides standard properties for event title and description,
    as well as a method to generate an all-day .ics Event.
    """

    @property
    def title(self) -> str:
        raise NotImplementedError("Subclasses must implement a title property.")

    @property
    def description(self) -> str:
        raise NotImplementedError("Subclasses must implement a description property.")

    def generate_event(self, event_date: date) -> Event:
        """
        Generate an all-day Event for the given event_date.
        """
        all_day_date = f"{event_date} 00:00:00"
        e = Event()
        e.name = self.title
        e.description = self.description
        e.begin = all_day_date
        e.end = all_day_date
        e.make_all_day()
        return e


class AppleHealthEvent(EventDescriptionMixIn, BaseModel):
    """
    An event derived from Apple Health data for usage within .ics format.
    """

    date: date
    _description: str
    title: str

    @property
    def description(self) -> str:
        return self._description


class AppleHealthData(BaseModel):
    """
    Holds all the data from Apple Health, parsed from AWS API Gateway and S3.
    """

    date: datetime
    date_updated: datetime
    name: str
    qty: float
    units: str
    source: Optional[str] = None

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, "%Y-%m-%d %H:%M:%S %z")
        return v

    @field_validator("date_updated", mode="before")
    @classmethod
    def parse_date_updated(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, "%Y-%m-%d %H:%M:%S.%f")
        return v


class Macros(EventDescriptionMixIn, BaseModel):
    """
    A basic food macros object.
    """

    carbohydrates: float = 0
    protein: float = 0
    total_fat: float = 0
    fiber: float = 0
    active_energy: float = 0

    @property
    def calories_ate(self) -> float:
        return (self.carbohydrates + self.protein) * 4 + self.total_fat * 9

    @property
    def macros(self) -> str:
        return f"{self.carbohydrates:.0f}C, {self.protein:.0f}P, {self.total_fat:.0f}F"

    @property
    def title(self) -> str:
        return f"🍽️ {self.calories_ate:.0f} cals ({self.macros})"

    @property
    def description(self) -> str:
        active_energy_adjusted = round(self.active_energy / 4, 2)
        return f"""
        🔥 {active_energy_adjusted:.0f} kcal
        🍽️ {self.calories_ate:.0f} kcal
        🥞 {self.macros}
        🍇 {self.fiber:.0f} g
        """


class Dailys(EventDescriptionMixIn, BaseModel):
    """
    A basic daily event.
    """

    apple_exercise_time: float = 0  # in minutes
    mindful_minutes: float = 0  # in minutes
    step_count: float = 0
    weight_body_mass: float = 0

    @property
    def apple_exercise_time_unit(self) -> TimeUnit:
        return TimeUnit(minutes=self.apple_exercise_time)

    @property
    def mindful_minutes_unit(self) -> TimeUnit:
        return TimeUnit(minutes=self.mindful_minutes)

    @property
    def activity_description(self) -> str:
        return f"🚴‍♂️ Activity: {self.apple_exercise_time_unit} active"

    @property
    def mindful_description(self) -> str:
        return f"🧘 Mindful: {self.mindful_minutes_unit.title_minutes_only} mindful"

    @property
    def step_count_description(self) -> str:
        return f"👣 Steps: {self.step_count:,.0f} steps"

    @property
    def weight_description(self) -> str:
        if self.weight_body_mass:
            return f"⚖️ Weight: {self.weight_body_mass:.0f} kg"
        return ""

    @property
    def description(self) -> str:
        return f"""
        {self.activity_description}
        {self.mindful_description}
        {self.step_count_description}
        {self.weight_description}
        """

    @property
    def title(self) -> str:
        mindful_title = f"🧠 {self.mindful_minutes_unit.title_minutes_only}"
        activity_title = f"🚴‍♂️ {self.apple_exercise_time_unit.hours}"
        step_title = f"👣 {self.step_count:,.0f} steps"
        weight_title = f"⚖️ {self.weight_body_mass:.1f} kg"
        return f"{mindful_title} | {activity_title} | {step_title} | {weight_title}"


class Sleep(EventDescriptionMixIn, BaseModel):
    """
    A basic sleep object.
    """

    sleep_analysis_asleep: float = 0  # in minutes
    sleep_analysis_inBed: float = 0  # in minutes
    sleep_analysis_sleepStart: Optional[str] = ""

    @property
    def time_asleep(self) -> TimeUnit:
        return TimeUnit(minutes=self.sleep_analysis_asleep)

    @property
    def time_in_bed(self) -> TimeUnit:
        return TimeUnit(minutes=self.sleep_analysis_inBed)

    @property
    def in_bed_time(self) -> str:
        if self.sleep_analysis_sleepStart:
            return convert_to_12_hr(self.sleep_analysis_sleepStart)
        return "No data"

    @property
    def efficiency(self) -> float:
        if self.time_in_bed.minutes:
            return self.time_asleep.minutes / self.time_in_bed.minutes * 100
        return 0

    @property
    def efficiency_title(self) -> str:
        return f"🛏️ {self.efficiency:.0f}%"

    @property
    def title(self) -> str:
        return f"💤 {self.time_asleep} ({self.in_bed_time})"

    @property
    def description(self) -> str:
        return f"""
        💤 Time asleep: {self.time_asleep}
        🛏️ Time in bed: {self.time_in_bed}
        🧮 Efficiency: {self.efficiency_title}
        """


def convert_to_12_hr(time_str: str) -> str:
    """Convert 24-hour time to 12-hour time."""
    time_as_24_hr = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S %z").time()
    time_as_12_hr = time_as_24_hr.strftime("%-I:%M %p")
    return time_as_12_hr
