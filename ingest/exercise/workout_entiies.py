from dataclasses import dataclass, field
from typing import Any, Optional

# --- Dataclass definitions using dict unpacking ---


@dataclass
class WorkoutSet:
    index: int
    type: str
    weight_kg: Optional[float]
    reps: Optional[int]
    distance_meters: Optional[float]
    duration_seconds: Optional[int]
    rpe: Optional[float]
    custom_metric: Optional[Any]


@dataclass
class Exercise:
    index: int
    title: str
    notes: str
    exercise_template_id: str
    superset_id: Optional[str]
    sets: list[WorkoutSet] = field(default_factory=list)


@dataclass
class Workout:
    id: str
    title: str
    description: str
    start_time: str
    end_time: str
    updated_at: str
    created_at: str
    exercises: list[Exercise] = field(default_factory=list)


@dataclass
class Event:
    type: str
    workout: Workout


# --- Parsing functions using dict unpacking ---


def parse_workout_set(data: dict[str, Any]) -> WorkoutSet:
    return WorkoutSet(**data)


def parse_exercise(data: dict[str, Any]) -> Exercise:
    sets = [parse_workout_set(s) for s in data.get("sets", [])]
    return Exercise(
        sets=sets,
        **{
            k: data[k]
            for k in ["index", "title", "notes", "exercise_template_id", "superset_id"]
            if k in data
        },
    )


def parse_workout(data: dict[str, Any]) -> Workout:
    exercises = [parse_exercise(ex) for ex in data.get("exercises", [])]
    return Workout(
        exercises=exercises,
        **{
            k: data[k]
            for k in [
                "id",
                "title",
                "description",
                "start_time",
                "end_time",
                "updated_at",
                "created_at",
            ]
            if k in data
        },
    )


def parse_event(data: dict[str, Any]) -> Event:
    return Event(type=data["type"], workout=parse_workout(data["workout"]))
