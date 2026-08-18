from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal

import polars as pl

from dashboard import export_web


def _write(tmp_path, name: str, rows: list[dict]) -> str:
    path = tmp_path / f"{name}.parquet"
    pl.DataFrame(rows).write_parquet(path)
    return str(path)


def _patch_tables(monkeypatch, tmp_path, tables: dict[str, list[dict]]):
    """Write each table's rows to its own parquet file and point `_path` at it."""
    paths = {name: _write(tmp_path, name, rows) for name, rows in tables.items()}
    monkeypatch.setattr(export_web, "_path", lambda table: paths[table])


class TestClean:
    def test_none_passes_through(self):
        assert export_web._clean(None) is None

    def test_date_becomes_iso_string(self):
        assert export_web._clean(date(2026, 3, 4)) == "2026-03-04"

    def test_datetime_truncates_to_date(self):
        assert export_web._clean(datetime(2026, 3, 4, 10, 30, 15)) == "2026-03-04"

    def test_decimal_converted_and_rounded(self):
        assert export_web._clean(Decimal("12.345")) == 12.35

    def test_whole_float_collapses_to_int(self):
        assert export_web._clean(12.0) == 12
        assert isinstance(export_web._clean(12.0), int)

    def test_fractional_float_rounds_to_2dp(self):
        assert export_web._clean(1.005) == 1.0
        assert export_web._clean(3.14159) == 3.14

    def test_other_types_pass_through_unchanged(self):
        assert export_web._clean("abc") == "abc"
        assert export_web._clean(3) == 3


class TestLatest:
    def test_picks_most_recent_non_null_per_key(self):
        daily = [
            {"a": 1, "b": None},
            {"a": None, "b": 2},
            {"a": 3, "b": None},
        ]
        assert export_web._latest(daily, ["a", "b"]) == {"a": 3, "b": 2}

    def test_missing_key_across_all_rows_is_none(self):
        daily = [{"a": 1}, {"a": None}]
        assert export_web._latest(daily, ["a", "b"]) == {"a": 1, "b": None}

    def test_empty_daily_list_returns_all_none(self):
        assert export_web._latest([], ["a", "b"]) == {"a": None, "b": None}


class TestBuildSnapshot:
    def test_snapshot_structure_and_content(self, monkeypatch, tmp_path):
        today = date.today()
        d0, d1, d2 = today - timedelta(days=2), today - timedelta(days=1), today

        tables = {
            "fct_daily_summary": [
                {
                    "date": d0,
                    "sleep_hours": 7.2,
                    "sleep_deep_hours": 1.4,
                    "sleep_rem_hours": 1.6,
                    "sleep_light_hours": 3.8,
                    "hrv_ms": 52.0,
                    "resting_hr_bpm": 54.0,
                    "vo2_max": 48.5,
                    "weight_kg": 70.1,
                    "bmi": 22.4,
                    "steps": 9500,
                    "protein_g": 160.0,
                    "carbs_g": 220.0,
                    "fat_g": 55.0,
                    "fiber_g": 30.0,
                    "water_ml": 2500.0,
                    "logged_calories": 2100.0,
                    "calculated_calories": 2200.0,
                    "workouts": 1,
                    "total_volume_kg": 4500.0,
                },
                {
                    "date": d1,
                    "sleep_hours": 6.9,
                    "sleep_deep_hours": 1.2,
                    "sleep_rem_hours": 1.5,
                    "sleep_light_hours": 3.6,
                    "hrv_ms": 50.0,
                    "resting_hr_bpm": 55.0,
                    "vo2_max": 48.6,
                    "weight_kg": 69.9,
                    "bmi": 22.3,
                    "steps": 10200,
                    "protein_g": 168.5,
                    "carbs_g": 230.0,
                    "fat_g": 58.0,
                    "fiber_g": 28.0,
                    "water_ml": 2600.0,
                    "logged_calories": 2150.0,
                    "calculated_calories": 2180.0,
                    "workouts": 0,
                    "total_volume_kg": 0.0,
                },
                {
                    # Newest row deliberately has nulls to exercise `_latest`'s
                    # look-back-through-history behaviour.
                    "date": d2,
                    "sleep_hours": None,
                    "sleep_deep_hours": None,
                    "sleep_rem_hours": None,
                    "sleep_light_hours": None,
                    "hrv_ms": None,
                    "resting_hr_bpm": None,
                    "vo2_max": None,
                    "weight_kg": 69.8,
                    "bmi": 22.3,
                    "steps": 500,
                    "protein_g": None,
                    "carbs_g": None,
                    "fat_g": None,
                    "fiber_g": None,
                    "water_ml": None,
                    "logged_calories": None,
                    "calculated_calories": None,
                    "workouts": 0,
                    "total_volume_kg": 0.0,
                },
            ],
            "fct_training_readiness": [
                {
                    "date": d1,
                    "readiness_score": 72.0,
                    "hrv_score": 70.0,
                    "rhr_score": 75.0,
                    "sleep_score": 68.0,
                    "deep_score": 60.0,
                    "hrv_ms": 50.0,
                    "resting_hr_bpm": 55.0,
                    "sleep_hours": 6.9,
                    "deep_sleep_ratio": 0.17,
                },
                {
                    "date": d2,
                    "readiness_score": 80.0,
                    "hrv_score": 78.0,
                    "rhr_score": 82.0,
                    "sleep_score": 75.0,
                    "deep_score": 65.0,
                    "hrv_ms": 53.0,
                    "resting_hr_bpm": 53.0,
                    "sleep_hours": 7.0,
                    "deep_sleep_ratio": 0.2,
                },
            ],
            "fct_weight_rolling_averages": [
                {"date": d1, "weight_kg": 69.9, "avg_7d": 70.0, "avg_30d": 70.5, "avg_60d": 71.0},
                {"date": d2, "weight_kg": 69.8, "avg_7d": 69.95, "avg_30d": 70.4, "avg_60d": 70.9},
            ],
            "fct_workouts": [
                {
                    "workout_date": d0,
                    "started_at": datetime.combine(d0, datetime.min.time()),
                    "workout_name": "Push Day",
                    "day_name": "Monday",
                    "workout_duration_minutes": 55.0,
                    "unique_exercises": 6,
                    "total_sets": 20,
                    "working_sets": 16,
                    "total_reps": 140,
                    "total_volume_kg": 4500.0,
                    "max_weight_kg": 100.0,
                    "avg_rpe": 7.5,
                },
                {
                    "workout_date": d1,
                    "started_at": datetime.combine(d1, datetime.min.time()),
                    "workout_name": "Pull Day",
                    "day_name": "Tuesday",
                    "workout_duration_minutes": 60.0,
                    "unique_exercises": 7,
                    "total_sets": 22,
                    "working_sets": 18,
                    "total_reps": 150,
                    "total_volume_kg": 4800.0,
                    "max_weight_kg": 110.0,
                    "avg_rpe": 8.0,
                },
            ],
            "fct_e1rm_rolling_total": [
                {
                    "workout_date": d0,
                    "squat_e1rm": 150.0,
                    "bench_e1rm": 100.0,
                    "deadlift_e1rm": 180.0,
                    "estimated_total": 430.0,
                },
                {
                    "workout_date": d1,
                    "squat_e1rm": 152.0,
                    "bench_e1rm": 101.0,
                    "deadlift_e1rm": 182.0,
                    "estimated_total": 435.0,
                },
            ],
            "fct_personal_bests": [
                {
                    "squat_pr_kg": 160.0,
                    "bench_pr_kg": 105.0,
                    "deadlift_pr_kg": 190.0,
                    "total_pr_kg": 455.0,
                    "best_dots": 350.0,
                    "best_wilks": 340.0,
                    "best_place": 3,
                    "total_competitions": 2,
                    "last_competition": d1,
                }
            ],
            "fct_nutrition_rolling_averages": [
                {
                    "date": d1,
                    "recorded_days_7d": 6,
                    "protein_avg_7d": 165.0,
                    "carbs_avg_7d": 225.0,
                    "fat_avg_7d": 57.0,
                    "calories_avg_7d": 2130.0,
                    "protein_avg_30d": 162.0,
                    "carbs_avg_30d": 228.0,
                    "fat_avg_30d": 56.5,
                    "calories_avg_30d": 2140.0,
                },
                {
                    "date": d2,
                    "recorded_days_7d": 7,
                    "protein_avg_7d": 166.0,
                    "carbs_avg_7d": 226.0,
                    "fat_avg_7d": 57.5,
                    "calories_avg_7d": 2135.0,
                    "protein_avg_30d": 162.5,
                    "carbs_avg_30d": 228.5,
                    "fat_avg_30d": 56.7,
                    "calories_avg_30d": 2141.0,
                },
            ],
            "fct_strava_activities": [
                {
                    "activity_date": d0,
                    "activity_name": "Morning Run",
                    "activity_type": "Run",
                    "distance_km": 8.2,
                    "moving_time_minutes": 42.0,
                    "elevation_gain_m": 60.0,
                    "avg_heartrate": 145.0,
                    "avg_pace_min_per_km": 5.1,
                    "avg_speed_kmh": 11.7,
                },
                {
                    "activity_date": d1,
                    "activity_name": "Evening Ride",
                    "activity_type": "Ride",
                    "distance_km": 25.0,
                    "moving_time_minutes": 55.0,
                    "elevation_gain_m": 120.0,
                    "avg_heartrate": 130.0,
                    "avg_pace_min_per_km": None,
                    "avg_speed_kmh": 27.3,
                },
            ],
        }
        _patch_tables(monkeypatch, tmp_path, tables)

        snapshot = export_web.build_snapshot()

        assert set(snapshot.keys()) == {
            "generated_at",
            "last_data_date",
            "today",
            "user_name",
            "goals",
            "latest",
            "daily",
            "readiness",
            "weight",
            "workouts",
            "e1rm",
            "prs",
            "macro_avg",
            "strava",
        }

        # `daily` is ordered ascending by date and dates are ISO strings.
        assert [row["date"] for row in snapshot["daily"]] == [
            d0.isoformat(),
            d1.isoformat(),
            d2.isoformat(),
        ]
        assert snapshot["last_data_date"] == d2.isoformat()

        # `latest` looks back through history for the most recent non-null value,
        # skipping the newest row's nulls for sleep/protein metrics.
        assert snapshot["latest"]["sleep_hours"] == 6.9
        assert snapshot["latest"]["protein_g"] == 168.5
        assert snapshot["latest"]["weight_kg"] == 69.8  # newest row has a value
        assert snapshot["latest"]["readiness_score"] == 80.0  # last readiness row

        # Whole-number floats collapse to int via `_clean`.
        assert snapshot["daily"][0]["steps"] == 9500
        assert isinstance(snapshot["daily"][0]["workouts"], int)

        # `workouts` preserves the row shape and orders newest-first.
        assert [w["workout_name"] for w in snapshot["workouts"]] == ["Pull Day", "Push Day"]
        assert snapshot["workouts"][0]["total_volume_kg"] == 4800.0
        assert "started_at" not in snapshot["workouts"][0]

        # `strava` orders newest-first and nulls survive as None.
        assert [s["activity_name"] for s in snapshot["strava"]] == [
            "Evening Ride",
            "Morning Run",
        ]
        assert snapshot["strava"][0]["avg_pace_min_per_km"] is None

        # `prs` and `macro_avg` collapse to a single flat dict (LIMIT 1 row).
        assert snapshot["prs"]["total_pr_kg"] == 455.0
        assert snapshot["prs"]["last_competition"] == d1.isoformat()
        assert snapshot["macro_avg"]["protein_avg_7d"] == 166.0  # latest by date DESC

        # `goals`/`user_name`/`today` come straight from dashboard.config.
        assert snapshot["goals"] == export_web.GOALS
        assert snapshot["user_name"] == export_web.USER_NAME
        assert snapshot["today"] == export_web.today_local().isoformat()

        # `generated_at` is a real, timezone-aware ISO timestamp.
        parsed = datetime.fromisoformat(snapshot["generated_at"])
        assert parsed.tzinfo is not None

        # The whole thing must be JSON-serialisable as produced.
        json.dumps(snapshot)

    def test_empty_single_row_tables_become_empty_dicts(self, monkeypatch, tmp_path):
        today = date.today()
        tables = {
            "fct_daily_summary": [
                {
                    "date": today,
                    "sleep_hours": 7.0,
                    "sleep_deep_hours": 1.5,
                    "sleep_rem_hours": 1.5,
                    "sleep_light_hours": 3.5,
                    "hrv_ms": 50.0,
                    "resting_hr_bpm": 55.0,
                    "vo2_max": 49.0,
                    "weight_kg": 70.0,
                    "bmi": 22.0,
                    "steps": 8000,
                    "protein_g": 150.0,
                    "carbs_g": 200.0,
                    "fat_g": 50.0,
                    "fiber_g": 25.0,
                    "water_ml": 2000.0,
                    "logged_calories": 2000.0,
                    "calculated_calories": 2000.0,
                    "workouts": 0,
                    "total_volume_kg": 0.0,
                }
            ],
            "fct_training_readiness": [],
            "fct_weight_rolling_averages": [],
            "fct_workouts": [],
            "fct_e1rm_rolling_total": [],
            "fct_personal_bests": [],
            "fct_nutrition_rolling_averages": [],
            "fct_strava_activities": [],
        }
        # Empty polars DataFrames need an explicit schema to still produce a
        # readable (zero-row) parquet file with the right columns.
        schemas = {
            "fct_training_readiness": {
                "date": pl.Date,
                "readiness_score": pl.Float64,
                "hrv_score": pl.Float64,
                "rhr_score": pl.Float64,
                "sleep_score": pl.Float64,
                "deep_score": pl.Float64,
                "hrv_ms": pl.Float64,
                "resting_hr_bpm": pl.Float64,
                "sleep_hours": pl.Float64,
                "deep_sleep_ratio": pl.Float64,
            },
            "fct_weight_rolling_averages": {
                "date": pl.Date,
                "weight_kg": pl.Float64,
                "avg_7d": pl.Float64,
                "avg_30d": pl.Float64,
                "avg_60d": pl.Float64,
            },
            "fct_workouts": {
                "workout_date": pl.Date,
                "started_at": pl.Datetime,
                "workout_name": pl.Utf8,
                "day_name": pl.Utf8,
                "workout_duration_minutes": pl.Float64,
                "unique_exercises": pl.Int64,
                "total_sets": pl.Int64,
                "working_sets": pl.Int64,
                "total_reps": pl.Int64,
                "total_volume_kg": pl.Float64,
                "max_weight_kg": pl.Float64,
                "avg_rpe": pl.Float64,
            },
            "fct_e1rm_rolling_total": {
                "workout_date": pl.Date,
                "squat_e1rm": pl.Float64,
                "bench_e1rm": pl.Float64,
                "deadlift_e1rm": pl.Float64,
                "estimated_total": pl.Float64,
            },
            "fct_personal_bests": {
                "squat_pr_kg": pl.Float64,
                "bench_pr_kg": pl.Float64,
                "deadlift_pr_kg": pl.Float64,
                "total_pr_kg": pl.Float64,
                "best_dots": pl.Float64,
                "best_wilks": pl.Float64,
                "best_place": pl.Int64,
                "total_competitions": pl.Int64,
                "last_competition": pl.Date,
            },
            "fct_nutrition_rolling_averages": {
                "date": pl.Date,
                "recorded_days_7d": pl.Int64,
                "protein_avg_7d": pl.Float64,
                "carbs_avg_7d": pl.Float64,
                "fat_avg_7d": pl.Float64,
                "calories_avg_7d": pl.Float64,
                "protein_avg_30d": pl.Float64,
                "carbs_avg_30d": pl.Float64,
                "fat_avg_30d": pl.Float64,
                "calories_avg_30d": pl.Float64,
            },
            "fct_strava_activities": {
                "activity_date": pl.Date,
                "activity_name": pl.Utf8,
                "activity_type": pl.Utf8,
                "distance_km": pl.Float64,
                "moving_time_minutes": pl.Float64,
                "elevation_gain_m": pl.Float64,
                "avg_heartrate": pl.Float64,
                "avg_pace_min_per_km": pl.Float64,
                "avg_speed_kmh": pl.Float64,
            },
        }

        paths = {}
        for name, rows in tables.items():
            path = tmp_path / f"{name}.parquet"
            if not rows and name in schemas:
                pl.DataFrame(schema=schemas[name]).write_parquet(path)
            else:
                pl.DataFrame(rows).write_parquet(path)
            paths[name] = str(path)
        monkeypatch.setattr(export_web, "_path", lambda table: paths[table])

        snapshot = export_web.build_snapshot()

        assert snapshot["prs"] == {}
        assert snapshot["macro_avg"] == {}
        assert snapshot["readiness"] == []
        assert snapshot["weight"] == []
        assert snapshot["workouts"] == []
        assert snapshot["e1rm"] == []
        assert snapshot["strava"] == []
        assert snapshot["latest"]["readiness_score"] is None
        assert snapshot["last_data_date"] == today.isoformat()


class TestRun:
    def test_run_writes_json_file(self, monkeypatch, tmp_path):
        canned = {"daily": [{"date": "2026-01-01"}], "last_data_date": "2026-01-01"}
        monkeypatch.setattr(export_web, "build_snapshot", lambda: canned)

        out_path = tmp_path / "web" / "data" / "dashboard.json"
        monkeypatch.setattr(export_web, "ROOT", tmp_path)  # keeps OUT_PATH.relative_to(ROOT) valid
        monkeypatch.setattr(export_web, "OUT_PATH", out_path)

        export_web.run()

        assert out_path.exists()
        assert json.loads(out_path.read_text()) == canned
