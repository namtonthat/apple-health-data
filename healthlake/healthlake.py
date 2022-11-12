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
class food:
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
class sleep:
    "Convert sleep"
    time: float

    @property
    def hours(self) -> float:
        hours = int(self.time)
        return hours

    @property
    def minutes(self) -> str:
        minutes = int((self.time - self._hours) * 60)
        return minutes

    @property
    def title(self) -> str:
        title = f"{self.hours}h {self.minutes}m"
        return title