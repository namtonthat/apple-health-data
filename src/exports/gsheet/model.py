"""Shared value types for the Google Sheets program export."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CellWrite:
    """A single pending cell write. row/col are 0-based grid indices."""

    row: int
    col: int
    value: str


@dataclass(frozen=True)
class DailyRow:
    """One day of health metrics from fct_daily_summary."""

    date: date
    weight_kg: float | None
    sleep_hours: float | None
    calories: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    fiber_g: float | None
    water_ml: float | None
    steps: float | None


@dataclass(frozen=True)
class SetRow:
    """One working set from fct_workout_sets (warmups excluded upstream)."""

    workout_id: str
    workout_date: date
    exercise_name: str
    set_number: int
    weight_kg: float | None
    reps: int | None
    rpe: float | None


def is_blank(cell: str) -> bool:
    """A cell is writable when empty or holding the RATE placeholder."""
    stripped = cell.strip()
    return stripped == "" or stripped.upper() == "RATE"


def fmt_num(v: float) -> str:
    """Format a number without trailing zeros: 97.5 -> '97.5', 150.0 -> '150'."""
    return f"{v:g}"
