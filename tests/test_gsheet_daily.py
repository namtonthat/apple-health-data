from datetime import date

import pytest

from exports.gsheet.daily import resolve_daily_writes
from exports.gsheet.model import DailyRow

HEADERS = [
    "DATE",
    "DAY",
    "COACH NOTES",
    "TARGET",
    "TOTAL HRS",
    "QUAL /10",
    "BODY WEIGHT",
    "CALORIES",
    "PROTEIN",
    "CARBS",
    "FAT",
    "FIBRE",
    "FLUID",
    "STEPS",
]
N = len(HEADERS)


def day_row(d: str, day: str) -> list[str]:
    row = [""] * N
    row[0], row[1] = d, day
    return row


def make_grid() -> list[list[str]]:
    grid = [["BANNER"] + [""] * (N - 1), HEADERS[:]]
    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    for i, day in enumerate(days):
        grid.append(day_row(f"{13 + i}/7/26", day))
    grid.append([""] * N)  # weekly average row
    return grid


def daily(d: date, **kw) -> DailyRow:
    defaults = dict(
        weight_kg=None,
        sleep_hours=None,
        calories=None,
        protein_g=None,
        carbs_g=None,
        fat_g=None,
        fiber_g=None,
        water_ml=None,
        steps=None,
    )
    defaults.update(kw)
    return DailyRow(date=d, **defaults)


def test_writes_weight_and_sleep_for_past_dates():
    grid = make_grid()
    rows = [daily(date(2026, 7, 13), weight_kg=70.34, sleep_hours=7.25)]
    result = resolve_daily_writes(grid, rows, today=date(2026, 7, 15))
    values = {(w.row, w.col): w.value for w in result.writes}
    assert values[(2, 6)] == "70.3"  # BODY WEIGHT, MON row
    assert values[(2, 4)] == "7.3"  # TOTAL HRS, MON row


def test_never_writes_today_or_future():
    grid = make_grid()
    rows = [daily(date(2026, 7, 15), weight_kg=70.0)]
    result = resolve_daily_writes(grid, rows, today=date(2026, 7, 15))
    assert result.writes == []


def test_skips_filled_cells():
    grid = make_grid()
    grid[2][6] = "70.1"  # bodyweight already filled by hand
    rows = [daily(date(2026, 7, 13), weight_kg=70.34)]
    result = resolve_daily_writes(grid, rows, today=date(2026, 7, 15))
    assert (2, 6) not in {(w.row, w.col) for w in result.writes}
    assert result.skipped == 1


def test_weekly_averages_on_completed_week():
    grid = make_grid()
    rows = [
        daily(
            date(2026, 7, 13),
            calories=2000,
            protein_g=120,
            carbs_g=300,
            fat_g=50,
            fiber_g=30,
            water_ml=2500,
            steps=10000,
        ),
        daily(
            date(2026, 7, 14),
            calories=2200,
            protein_g=140,
            carbs_g=320,
            fat_g=60,
            fiber_g=34,
            water_ml=3500,
            steps=12000,
        ),
    ]
    result = resolve_daily_writes(grid, rows, today=date(2026, 7, 20))
    avg_row = 9  # row after SUN
    values = {(w.row, w.col): w.value for w in result.writes}
    assert values[(avg_row, 7)] == "2100"  # CALORIES
    assert values[(avg_row, 8)] == "130"  # PROTEIN
    assert values[(avg_row, 12)] == "3.0"  # FLUID litres
    assert values[(avg_row, 13)] == "11000"  # STEPS


def test_no_averages_for_incomplete_week():
    grid = make_grid()
    rows = [daily(date(2026, 7, 13), calories=2000)]
    result = resolve_daily_writes(grid, rows, today=date(2026, 7, 17))
    avg_row_writes = [w for w in result.writes if w.row == 9]
    assert avg_row_writes == []


def test_weekly_averages_half_up_rounding_integers():
    """Test that .5 ties round up (2000.5 -> 2001, not banker's 2000)."""
    grid = make_grid()
    rows = [
        daily(date(2026, 7, 13), calories=2000),
        daily(date(2026, 7, 14), calories=2001),
    ]
    result = resolve_daily_writes(grid, rows, today=date(2026, 7, 20))
    avg_row = 9
    values = {(w.row, w.col): w.value for w in result.writes}
    # Mean of 2000 and 2001 is 2000.5; should round up to 2001
    assert values[(avg_row, 7)] == "2001"  # CALORIES


def test_weekly_averages_half_up_rounding_fluid():
    """Test that FLUID .5 ties round up (2.25 -> 2.3, not banker's 2.2)."""
    grid = make_grid()
    rows = [
        daily(date(2026, 7, 13), water_ml=2100),
        daily(date(2026, 7, 14), water_ml=2400),
    ]
    result = resolve_daily_writes(grid, rows, today=date(2026, 7, 20))
    avg_row = 9
    values = {(w.row, w.col): w.value for w in result.writes}
    # Mean of 2100 and 2400 is 2250; 2250/1000 = 2.25; should round up to 2.3
    assert values[(avg_row, 12)] == "2.3"  # FLUID litres


def test_missing_header_raises():
    grid = [["DATE", "DAY"]]  # no BODY WEIGHT anywhere
    with pytest.raises(ValueError, match="BODY WEIGHT"):
        resolve_daily_writes(grid, [], today=date(2026, 7, 20))
