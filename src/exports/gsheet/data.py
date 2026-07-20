"""Read transformed pipeline data for the gsheet export.

Same duckdb-over-S3-parquet pattern as pipelines/pipelines/export_to_ics.py.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import duckdb

from exports.gsheet.model import DailyRow, SetRow


def _default_source(table: str) -> str:
    bucket = os.environ["S3_BUCKET_NAME"]
    return f"s3://{bucket}/transformed/{table}"


def _to_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def load_daily_rows(conn: duckdb.DuckDBPyConnection, source: str | None = None) -> list[DailyRow]:
    source = source or _default_source("fct_daily_summary")
    result = conn.execute(f"""
        SELECT date, weight_kg, sleep_hours, logged_calories, protein_g,
               carbs_g, fat_g, fiber_g, water_ml, steps
        FROM read_parquet('{source}')
        ORDER BY date
    """).fetchall()
    return [
        DailyRow(
            date=_to_date(row[0]),
            weight_kg=float(row[1]) if row[1] is not None else None,
            sleep_hours=float(row[2]) if row[2] is not None else None,
            calories=float(row[3]) if row[3] is not None else None,
            protein_g=float(row[4]) if row[4] is not None else None,
            carbs_g=float(row[5]) if row[5] is not None else None,
            fat_g=float(row[6]) if row[6] is not None else None,
            fiber_g=float(row[7]) if row[7] is not None else None,
            water_ml=float(row[8]) if row[8] is not None else None,
            steps=int(row[9]) if row[9] is not None else None,
        )
        for row in result
    ]


def load_week_sets(
    conn: duckdb.DuckDBPyConnection, week_monday: date, source: str | None = None
) -> list[SetRow]:
    source = source or _default_source("fct_workout_sets")
    week_sunday = week_monday + timedelta(days=6)
    result = conn.execute(
        f"""
        SELECT workout_id, workout_date, exercise_name, set_number,
               weight_kg, reps, rpe
        FROM read_parquet('{source}')
        WHERE set_type != 'warmup'
          AND workout_date BETWEEN ? AND ?
        ORDER BY workout_date, workout_id, exercise_name, set_number
        """,
        [week_monday, week_sunday],
    ).fetchall()
    return [
        SetRow(
            workout_id=str(row[0]),
            workout_date=_to_date(row[1]),
            exercise_name=row[2],
            set_number=int(row[3]),
            weight_kg=row[4],
            reps=int(row[5]) if row[5] is not None else None,
            rpe=row[6],
        )
        for row in result
    ]
