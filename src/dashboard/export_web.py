"""Export a consolidated JSON snapshot for the static web dashboard.

Reads the same transformed/ parquet the Streamlit dashboard uses, but with no
Streamlit dependency, so it can run headless in CI. Writes web/data/dashboard.json
which the Next.js + Tremor app bundles at build time.

    uv run python run.py export-web
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from dashboard.config import (
    AWS_REGION,
    GOALS,
    S3_BUCKET,
    S3_TRANSFORMED_PREFIX,
    USER_NAME,
    today_local,
)

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_PATH = ROOT / "web" / "data" / "dashboard.json"

# How much history to ship (keeps the JSON small and the charts readable).
DAILY_DAYS = 120
READINESS_DAYS = 120
WEIGHT_DAYS = 180
WORKOUTS_LIMIT = 24
STRAVA_LIMIT = 16


def _connect() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    conn.execute(f"SET s3_region = '{AWS_REGION}'")
    conn.execute(f"SET s3_access_key_id = '{os.environ.get('AWS_ACCESS_KEY_ID', '')}'")
    conn.execute(f"SET s3_secret_access_key = '{os.environ.get('AWS_SECRET_ACCESS_KEY', '')}'")
    return conn


def _path(table: str) -> str:
    return f"s3://{S3_BUCKET}/{S3_TRANSFORMED_PREFIX}/{table}"


def _clean(value: Any) -> Any:
    """Make a DuckDB value JSON-serialisable and tidy."""
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, float):
        # round to 2dp; collapse whole numbers to int for compact JSON
        rounded = round(value, 2)
        return int(rounded) if rounded.is_integer() else rounded
    return value


def _rows(conn: duckdb.DuckDBPyConnection, query: str) -> list[dict[str, Any]]:
    cur = conn.execute(query)
    cols = [d[0] for d in cur.description]
    return [{c: _clean(v) for c, v in zip(cols, row)} for row in cur.fetchall()]


def _latest(daily: list[dict[str, Any]], keys: list[str]) -> dict[str, Any]:
    """Most recent non-null value per key across the daily series (newest last)."""
    out: dict[str, Any] = {}
    for key in keys:
        for row in reversed(daily):
            if row.get(key) is not None:
                out[key] = row[key]
                break
        else:
            out[key] = None
    return out


def build_snapshot() -> dict[str, Any]:
    conn = _connect()

    daily = _rows(
        conn,
        f"""
        SELECT date, sleep_hours, sleep_deep_hours, sleep_rem_hours, sleep_light_hours,
               hrv_ms, resting_hr_bpm, vo2_max, weight_kg, bmi, steps,
               protein_g, carbs_g, fat_g, fiber_g, water_ml,
               logged_calories, calculated_calories, workouts, total_volume_kg
        FROM read_parquet('{_path("fct_daily_summary")}')
        WHERE date >= current_date - INTERVAL {DAILY_DAYS} DAY
        ORDER BY date
        """,
    )

    readiness = _rows(
        conn,
        f"""
        SELECT date, readiness_score, hrv_score, rhr_score, sleep_score, deep_score,
               hrv_ms, resting_hr_bpm, sleep_hours, deep_sleep_ratio
        FROM read_parquet('{_path("fct_training_readiness")}')
        WHERE date >= current_date - INTERVAL {READINESS_DAYS} DAY
        ORDER BY date
        """,
    )

    weight = _rows(
        conn,
        f"""
        SELECT date, weight_kg, avg_7d, avg_30d, avg_60d
        FROM read_parquet('{_path("fct_weight_rolling_averages")}')
        WHERE date >= current_date - INTERVAL {WEIGHT_DAYS} DAY
        ORDER BY date
        """,
    )

    workouts = _rows(
        conn,
        f"""
        SELECT workout_date, workout_name, day_name, workout_duration_minutes,
               unique_exercises, total_sets, working_sets, total_reps,
               total_volume_kg, max_weight_kg, avg_rpe
        FROM read_parquet('{_path("fct_workouts")}')
        ORDER BY workout_date DESC, started_at DESC
        LIMIT {WORKOUTS_LIMIT}
        """,
    )

    e1rm = _rows(
        conn,
        f"""
        SELECT workout_date, squat_e1rm, bench_e1rm, deadlift_e1rm, estimated_total
        FROM read_parquet('{_path("fct_e1rm_rolling_total")}')
        ORDER BY workout_date
        """,
    )

    prs_rows = _rows(
        conn,
        f"""
        SELECT squat_pr_kg, bench_pr_kg, deadlift_pr_kg, total_pr_kg,
               best_dots, best_wilks, best_place, total_competitions, last_competition
        FROM read_parquet('{_path("fct_personal_bests")}')
        LIMIT 1
        """,
    )
    prs = prs_rows[0] if prs_rows else {}

    macro_avg_rows = _rows(
        conn,
        f"""
        SELECT recorded_days_7d,
               protein_avg_7d, carbs_avg_7d, fat_avg_7d, calories_avg_7d,
               protein_avg_30d, carbs_avg_30d, fat_avg_30d, calories_avg_30d
        FROM read_parquet('{_path("fct_nutrition_rolling_averages")}')
        ORDER BY date DESC
        LIMIT 1
        """,
    )
    macro_avg = macro_avg_rows[0] if macro_avg_rows else {}

    strava = _rows(
        conn,
        f"""
        SELECT activity_date, activity_name, activity_type, distance_km,
               moving_time_minutes, elevation_gain_m, avg_heartrate,
               avg_pace_min_per_km, avg_speed_kmh
        FROM read_parquet('{_path("fct_strava_activities")}')
        ORDER BY activity_date DESC
        LIMIT {STRAVA_LIMIT}
        """,
    )

    conn.close()

    latest_keys = [
        "sleep_hours",
        "sleep_deep_hours",
        "sleep_rem_hours",
        "sleep_light_hours",
        "hrv_ms",
        "resting_hr_bpm",
        "vo2_max",
        "weight_kg",
        "bmi",
        "steps",
        "protein_g",
        "carbs_g",
        "fat_g",
        "water_ml",
        "logged_calories",
        "total_volume_kg",
    ]
    latest = _latest(daily, latest_keys)
    latest["readiness_score"] = readiness[-1]["readiness_score"] if readiness else None

    last_data_date = daily[-1]["date"] if daily else None

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "last_data_date": last_data_date,
        "today": today_local().isoformat(),
        "user_name": USER_NAME,
        "goals": GOALS,
        "latest": latest,
        "daily": daily,
        "readiness": readiness,
        "weight": weight,
        "workouts": workouts,
        "e1rm": e1rm,
        "prs": prs,
        "macro_avg": macro_avg,
        "strava": strava,
    }


def run() -> None:
    snapshot = build_snapshot()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(snapshot, indent=2))
    print(
        f"Wrote {OUT_PATH.relative_to(ROOT)} "
        f"({len(snapshot['daily'])} days, data as of {snapshot['last_data_date']})"
    )


if __name__ == "__main__":
    run()
