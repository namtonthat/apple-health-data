## Rewrite of `apple-health.py` using dataclasses to encapsulate methods instead
import requests
import os
import glob
import pandas as pd
from ics import Calendar, Event
from dataclasses import dataclass


import logging
logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


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
        title = f"{self.hours}h {self.minutes}m"
        return title


@dataclass
class Food:
    carbs: float
    protein: float
    fat: float
    fiber: float

    @property
    def calories(self) -> float:
        calories = (self.carbs + self.protein) * 4 + (self.fat) * 9
        return calories

    @property
    def title(self) -> str:
        title = f"🔥 {self.calories:.0f} cals ({self.carbs:.0f}C, {self.protein:.0f}P, {self.fat:.0f}F)"
        return title

    @property
    def description(self) -> str:
        description = f"""
        🔥 {self.calories:.0f} kcal
        🥞 {self.title}
        🍇 {self.fiber:.0f}
        """
        return description

@dataclass
class Sleep:
    time_asleep: Time
    time_in_bed: Time

    # time in which you were in bed
    time_sleep: str

    @property
    def efficiency(self) -> float:
        efficiency = self.time_asleep.time / self.time_in_bed.time * 100
        return efficiency

    @property
    def efficiency_title(self) -> str:
        efficiency_title = f"{self.efficiency:.0f}%"
        return efficiency_title

    @property
    def title(self) -> str:
        title = f"💤 {self.time_asleep.title} ({self.time_sleep})"
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
    activity_mins: Time
    mindful_mins: Time

    @property
    def activity_title(self) -> str:
        title = f"{self.activity_mins.title} active"
        return title

    @property
    def mindful_title(self) -> str:
        title = f"{self.mindful_mins.minutes} mins mindful"
        return title

    @property
    def title(self) -> str:
        title = f"🧠 {self.mindful_title}"

    @property
    def description(self) -> str:
        description = f"""
        🚴‍♂️ Activity: {self.activity_title}
        🧘 Mindful: {self.mindful_title}
        """
        return description