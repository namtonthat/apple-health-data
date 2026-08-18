"""Smoke tests for the Streamlit dashboard pages.

Each page loads data through the public ``load_*`` wrappers in
``dashboard.data``. Those wrappers are monkeypatched here to return small,
in-memory Polars DataFrames so the pages never touch S3/DuckDB/network during
a test run. Pages are executed end-to-end via ``AppTest`` and asserted to
render without raising.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import polars as pl
import pytest
from streamlit.testing.v1 import AppTest

from dashboard import config, data

DASHBOARD_DIR = Path(__file__).resolve().parents[1] / "src" / "dashboard"

HOME_PAGE = DASHBOARD_DIR / "Home.py"
RECOVERY_PAGE = DASHBOARD_DIR / "pages" / "1_Recovery.py"
NUTRITION_PAGE = DASHBOARD_DIR / "pages" / "2_Nutrition_&_Body.py"
EXERCISES_PAGE = DASHBOARD_DIR / "pages" / "3_Exercises.py"
INSIGHTS_PAGE = DASHBOARD_DIR / "pages" / "4_Performance_Insights.py"

RUN_TIMEOUT = 30


def _recent_dates(n: int) -> list[date]:
    """``n`` consecutive dates ending today (in the dashboard's own timezone).

    Using ``config.today_local()`` (a pure, local computation -- no network)
    keeps these aligned with whatever "today" the pages themselves compute
    when building their default date-filter windows.
    """
    today = config.today_local()
    return [today - timedelta(days=i) for i in range(n - 1, -1, -1)]


def _daily_summary_frame(dates: list[date]) -> pl.DataFrame:
    n = len(dates)
    return pl.DataFrame(
        {
            "date": dates,
            "sleep_hours": [6.5 + 0.1 * i for i in range(n)],
            "sleep_deep_hours": [1.2 + 0.02 * i for i in range(n)],
            "sleep_rem_hours": [1.4 + 0.02 * i for i in range(n)],
            "sleep_light_hours": [3.3 + 0.02 * i for i in range(n)],
            "resting_hr_bpm": [58.0 - 0.2 * i for i in range(n)],
            "hrv_ms": [45.0 + 0.5 * i for i in range(n)],
            "vo2_max": [42.0 + 0.1 * i for i in range(n)],
            "weight_kg": [78.0 - 0.05 * i for i in range(n)],
            "steps": [8000.0 + 100 * i for i in range(n)],
            "walking_asymmetry_pct": [3.0 + 0.1 * (i % 5) for i in range(n)],
            "meditation_minutes": [10.0 + i for i in range(n)],
            "protein_g": [150.0 + 2 * i for i in range(n)],
            "carbs_g": [220.0 + 3 * i for i in range(n)],
            "fat_g": [55.0 + i for i in range(n)],
            "fiber_g": [25.0 + 0.5 * i for i in range(n)],
            "water_ml": [2000.0 + 20 * i for i in range(n)],
            "logged_calories": [2200.0 + 15 * i for i in range(n)],
            "macro_calories": [2200.0 + 15 * i for i in range(n)],
            "had_strength_workout": [True] * n,
            "total_volume_kg": [4000.0 + 50 * i for i in range(n)],
            "avg_rpe": [7.0 + 0.05 * (i % 4) for i in range(n)],
            "workout_duration_minutes": [60.0 + i for i in range(n)],
        }
    )


def _weight_rolling_averages_frame(dates: list[date]) -> pl.DataFrame:
    n = len(dates)
    return pl.DataFrame(
        {
            "date": dates,
            "avg_7d": [78.0 - 0.05 * i for i in range(n)],
            "avg_14d": [78.1 - 0.04 * i for i in range(n)],
            "avg_30d": [78.2 - 0.03 * i for i in range(n)],
            "avg_60d": [78.3 - 0.02 * i for i in range(n)],
            "avg_120d": [78.4 - 0.01 * i for i in range(n)],
        }
    )


def _workouts_frame(dates: list[date]) -> pl.DataFrame:
    recent = dates[-2:]  # a couple of sessions inside the default filter window
    return pl.DataFrame(
        {
            "workout_date": recent,
            "workout_name": ["Push Day", "Leg Day"],
            "started_at": [
                f"{recent[0].isoformat()}T18:00:00",
                f"{recent[1].isoformat()}T18:00:00",
            ],
            "ended_at": [
                f"{recent[0].isoformat()}T19:00:00",
                f"{recent[1].isoformat()}T19:15:00",
            ],
            "workout_duration_minutes": [60.0, 75.0],
        }
    ).with_columns(
        pl.col("started_at").str.to_datetime(),
        pl.col("ended_at").str.to_datetime(),
    )


def _training_readiness_frame(dates: list[date]) -> pl.DataFrame:
    n = len(dates)
    return pl.DataFrame(
        {
            "date": dates,
            "readiness_score": [60.0 + (i % 5) * 5 for i in range(n)],
            "hrv_score": [18.0 + (i % 3) for i in range(n)],
            "rhr_score": [17.0 + (i % 4) for i in range(n)],
            "sleep_score": [19.0 + (i % 2) for i in range(n)],
            "deep_score": [16.0 + (i % 3) for i in range(n)],
        }
    )


def _workout_sets_frame(dates: list[date]) -> pl.DataFrame:
    workout_date = dates[-1]
    started_at = f"{workout_date.isoformat()}T18:00:00"
    exercises = [
        ("Squat (Barbell)", 1, 100.0, 5, "warmup", 1, 1),
        ("Squat (Barbell)", 2, 140.0, 5, "normal", 1, 2),
        ("Bench Press (Barbell)", 1, 80.0, 5, "normal", 2, 1),
        ("Sumo Deadlift", 1, 160.0, 3, "normal", 3, 1),
        ("Leg Press (Machine)", 1, 200.0, 10, "normal", 4, 1),
    ]
    return pl.DataFrame(
        {
            "workout_date": [workout_date] * len(exercises),
            "workout_name": ["Leg Day"] * len(exercises),
            "exercise_name": [e[0] for e in exercises],
            "exercise_order": [e[5] for e in exercises],
            "set_number": [e[6] for e in exercises],
            "weight_kg": [e[2] for e in exercises],
            "reps": [e[3] for e in exercises],
            "volume_kg": [e[2] * e[3] for e in exercises],
            "est_1rm": [e[2] * (1 + e[3] / 30) for e in exercises],
            "rpe": [8.0] * len(exercises),
            "set_type": [e[4] for e in exercises],
            "started_at": [started_at] * len(exercises),
        }
    ).with_columns(pl.col("started_at").str.to_datetime())


def _big3_prs_frame(dates: list[date]) -> pl.DataFrame:
    pr_date = dates[-1]
    return pl.DataFrame(
        {
            "lift": ["squat", "bench", "deadlift"],
            "best_e1rm": [150.0, 100.0, 180.0],
            "best_weight_kg": [140.0, 90.0, 160.0],
            "best_reps": [5, 5, 3],
            "pr_date": [pr_date, pr_date, pr_date],
        }
    )


def _personal_bests_frame(dates: list[date]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "squat_pr_kg": [145.0],
            "bench_pr_kg": [95.0],
            "deadlift_pr_kg": [175.0],
            "total_pr_kg": [415.0],
            "last_competition": [dates[0]],
        }
    )


def _e1rm_rolling_total_frame(dates: list[date]) -> pl.DataFrame:
    n = len(dates)
    return pl.DataFrame(
        {
            "workout_date": dates,
            "squat_e1rm": [140.0 + i for i in range(n)],
            "bench_e1rm": [90.0 + 0.5 * i for i in range(n)],
            "deadlift_e1rm": [170.0 + i for i in range(n)],
            "estimated_total": [400.0 + 2.5 * i for i in range(n)],
        }
    )


def _strava_activities_frame(dates: list[date]) -> pl.DataFrame:
    recent = dates[-2:]
    return pl.DataFrame(
        {
            "activity_date": recent,
            "activity_name": ["Morning Run", "Evening Ride"],
            "activity_type": ["Run", "Ride"],
            "distance_km": [8.2, 25.0],
            "moving_time_minutes": [45.0, 60.0],
            "elevation_gain_m": [50.0, 200.0],
            "avg_heartrate": [145.0, 130.0],
            "avg_pace_min_per_km": [5.5, 0.0],
            "max_heartrate": [165.0, 150.0],
            "pr_count": [1, 0],
        }
    )


@pytest.fixture
def patched_loaders(monkeypatch):
    """Patch every public ``load_*`` wrapper in ``dashboard.data`` to return
    small, deterministic Polars frames instead of hitting S3/DuckDB.

    Pages import these by name (``from dashboard.data import load_x``), and
    ``AppTest`` re-executes each page's top-level code on every ``.run()``, so
    patching the attribute on the ``dashboard.data`` module is picked up the
    next time a page's ``from ... import ...`` statement runs.
    """
    dates = _recent_dates(14)
    frames = {
        "load_daily_summary": _daily_summary_frame(dates),
        "load_weight_rolling_averages": _weight_rolling_averages_frame(dates),
        "load_workouts": _workouts_frame(dates),
        "load_training_readiness": _training_readiness_frame(dates),
        "load_workout_sets": _workout_sets_frame(dates),
        "load_big3_prs": _big3_prs_frame(dates),
        "load_personal_bests": _personal_bests_frame(dates),
        "load_e1rm_rolling_total": _e1rm_rolling_total_frame(dates),
        "load_strava_activities": _strava_activities_frame(dates),
    }
    for name, frame in frames.items():
        monkeypatch.setattr(data, name, lambda frame=frame: frame)
    return frames


def test_home_page_renders_without_exception():
    at = AppTest.from_file(str(HOME_PAGE))
    at.run(timeout=RUN_TIMEOUT)

    assert not at.exception
    assert len(at.title) == 1


def test_recovery_page_renders_without_exception(patched_loaders):
    at = AppTest.from_file(str(RECOVERY_PAGE))
    at.run(timeout=RUN_TIMEOUT)

    assert not at.exception
    assert len(at.header) > 0


def test_nutrition_and_body_page_renders_without_exception(patched_loaders):
    at = AppTest.from_file(str(NUTRITION_PAGE))
    at.run(timeout=RUN_TIMEOUT)

    assert not at.exception
    assert len(at.header) > 0


def test_exercises_page_renders_without_exception(patched_loaders):
    at = AppTest.from_file(str(EXERCISES_PAGE))
    at.run(timeout=RUN_TIMEOUT)

    assert not at.exception
    assert len(at.header) > 0


def test_performance_insights_page_renders_without_exception(patched_loaders):
    at = AppTest.from_file(str(INSIGHTS_PAGE))
    at.run(timeout=RUN_TIMEOUT)

    assert not at.exception
    assert len(at.header) > 0
