from datetime import date

import duckdb
import pytest

from exports.gsheet.data import load_daily_rows, load_week_sets


@pytest.fixture
def conn():
    return duckdb.connect(":memory:")


def test_load_daily_rows(conn, tmp_path):
    path = str(tmp_path / "daily.parquet")
    conn.execute(f"""
        COPY (
            SELECT DATE '2026-07-13' AS date, 70.3 AS weight_kg, 7.2 AS sleep_hours,
                   2000.0 AS logged_calories, 120.0 AS protein_g, 300.0 AS carbs_g,
                   50.0 AS fat_g, 30.0 AS fiber_g, 2500.0 AS water_ml, 10000 AS steps
        ) TO '{path}' (FORMAT PARQUET)
    """)
    rows = load_daily_rows(conn, source=path)
    assert len(rows) == 1
    r = rows[0]
    assert r.date == date(2026, 7, 13)
    assert r.weight_kg == 70.3
    assert r.calories == 2000.0
    assert r.steps == 10000


def test_load_week_sets_filters_week_and_warmups(conn, tmp_path):
    path = str(tmp_path / "sets.parquet")
    conn.execute(f"""
        COPY (
            SELECT * FROM (VALUES
                ('s1', 'w1', DATE '2026-07-13', 'Bench Press (Barbell)', 1,
                 'normal', 80.0, 8, 7.5),
                ('s2', 'w1', DATE '2026-07-13', 'Bench Press (Barbell)', 2,
                 'warmup', 60.0, 5, NULL),
                ('s3', 'w2', DATE '2026-07-25', 'Bench Press (Barbell)', 1,
                 'normal', 85.0, 5, 8.0)
            ) AS t(set_id, workout_id, workout_date, exercise_name, set_number,
                   set_type, weight_kg, reps, rpe)
        ) TO '{path}' (FORMAT PARQUET)
    """)
    sets = load_week_sets(conn, week_monday=date(2026, 7, 13), source=path)
    assert len(sets) == 1  # warmup excluded, other week excluded
    s = sets[0]
    assert s.workout_id == "w1"
    assert s.set_number == 1
    assert s.rpe == 7.5
