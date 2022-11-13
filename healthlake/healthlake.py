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
        title = f"{self.carbs}g C, {self.protein}g P, {self.fat}g F"
        return title

@dataclass
class Sleep:
    time_asleep: Time
    time_in_bed: Time

    @property
    def efficiency(self) -> float:
        efficiency = self.time_asleep.time / self.time_in_bed.time * 100
        return efficiency

    @property
    def efficiency_title(self) -> str:
        title = f"{self.efficiency:.0f}%"
        return title


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