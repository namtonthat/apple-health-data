from abc import ABC, abstractmethod
from datetime import date
from typing import Any
from ics import Event
from pydantic import BaseModel


class AppleHealthEvent(BaseModel):
    date: date
    _description: str
    event_title: str

    @property
    def title(self) -> str:
        return self.event_title

    @property
    def description(self) -> str:
        return self._description

    @property
    def event(self) -> Event:
        e = Event()
        e.name = self.title
        e.description = self.description
        # Create an all-day event using the provided date
        e.begin = f"{self.date} 00:00:00"
        e.end = f"{self.date} 00:00:00"
        e.make_all_day()
        return e


# Abstract base class for event creation
class BaseHealthEventCreator(ABC):
    @classmethod
    @abstractmethod
    def create_from_stats(cls, stats: dict[str, Any], event_date: str) -> Event:
        """
        Create and return an ICS Event based on the provided stats and event_date.
        """
        pass


class FoodEvent(BaseHealthEventCreator):
    @classmethod
    def create_from_stats(cls, stats: dict[str, Any], event_date: str) -> Event:
        # For demonstration, assume stats contains a 'calories' key.
        title = f"Food: {stats.get('calories', 0)} cals"
        description = "Food event details: " + ", ".join(
            f"{k}: {v}" for k, v in stats.items()
        )
        event_model = AppleHealthEvent(
            date=date.fromisoformat(event_date),
            event_title=title,
            _description=description,
        )
        return event_model.event


class ActivityEvent(BaseHealthEventCreator):
    @classmethod
    def create_from_stats(cls, stats: dict[str, Any], event_date: str) -> Event:
        title = f"Activity: {stats.get('duration', 0)} mins"
        description = "Activity event details: " + ", ".join(
            f"{k}: {v}" for k, v in stats.items()
        )
        event_model = AppleHealthEvent(
            date=date.fromisoformat(event_date),
            event_title=title,
            _description=description,
        )
        return event_model.event


class SleepEvent(BaseHealthEventCreator):
    @classmethod
    def create_from_stats(cls, stats: dict[str, Any], event_date: str) -> Event:
        title = f"Sleep: {stats.get('sleep_hours', 0)} hrs"
        description = "Sleep event details: " + ", ".join(
            f"{k}: {v}" for k, v in stats.items()
        )
        event_model = AppleHealthEvent(
            date=date.fromisoformat(event_date),
            event_title=title,
            _description=description,
        )
        return event_model.event


class DailysEvent(BaseHealthEventCreator):
    @classmethod
    def create_from_stats(cls, stats: dict[str, Any], event_date: str) -> Event:
        """
        Creates an event for daily metrics that might include multiple measurements.
        Expected keys (example):
            - apple_exercise_time (in minutes)
            - mindful_minutes (in minutes)
            - step_count (integer)
            - weight_body_mass (float, kg)
        """
        apple_exercise_time = stats.get("apple_exercise_time", 0)
        mindful_minutes = stats.get("mindful_minutes", 0)
        step_count = stats.get("step_count", 0)
        weight_body_mass = stats.get("weight_body_mass", 0)

        # Build descriptions for each metric
        activity_desc = f"🚴‍♂️ Activity: {apple_exercise_time} active"
        mindful_desc = f"🧘 Mindful: {mindful_minutes}m mindful"
        step_desc = f"👣 Steps: {step_count:,.0f} steps"
        weight_desc = f"⚖️ Weight: {weight_body_mass:.1f} kg" if weight_body_mass else ""

        # Combine into a multi-line description
        description = "\n".join(
            filter(None, [activity_desc, mindful_desc, step_desc, weight_desc])
        )
        # Build a composite title
        title = f"🧠 {mindful_minutes}m | 🚴‍♂️ {apple_exercise_time}m | 👣 {step_count:,.0f} steps | ⚖️ {weight_body_mass:.1f} kg"

        event_model = AppleHealthEvent(
            date=date.fromisoformat(event_date),
            event_title=title,
            _description=description,
        )
        return event_model.event
