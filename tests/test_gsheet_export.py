from datetime import date

from exports.gsheet.config import ExportConfig
from exports.gsheet.export import plan_writes
from exports.gsheet.model import SetRow

CFG = ExportConfig(
    spreadsheet_id="x",
    daily_tab="Daily",
    block_tab="Block",
    week1_monday=date(2026, 7, 13),
    exercise_map={"COMP BENCH": "Bench Press (Barbell)"},
)

DAILY_GRID = [
    [
        "DATE",
        "DAY",
        "TOTAL HRS",
        "BODY WEIGHT",
        "CALORIES",
        "PROTEIN",
        "CARBS",
        "FAT",
        "FIBRE",
        "FLUID",
        "STEPS",
    ],
    ["13/7/26", "MON", "", "", "", "", "", "", "", "", ""],
]

# Two week groups: week 1 (cols 2-5) and week 2 (cols 6-9), so the previous
# and current-in-progress windows write into disjoint columns.
BLOCK_GRID = [
    [
        "MOVEMENT",
        "SETSxREPS",
        "TARGET",
        "REPS",
        "LOAD",
        "ACTUAL",
        "TARGET",
        "REPS",
        "LOAD",
        "ACTUAL",
    ],
    ["COMP BENCH", "3x5", "RPE 7", "", "", "RATE", "RPE 8", "", "", "RATE"],
]


def _set(workout_date: date, wid: str, kg: float, reps: int, rpe: float) -> SetRow:
    return SetRow(
        workout_id=wid,
        workout_date=workout_date,
        exercise_name="Bench Press (Barbell)",
        set_number=1,
        weight_kg=kg,
        reps=reps,
        rpe=rpe,
    )


def test_plan_writes_covers_both_previous_and_current_week():
    """week1_monday=2026-07-13; today=2026-07-22 (Wed) -> current_monday=2026-07-20
    (week index 1), prev_monday=2026-07-13 (week index 0). Both windows are
    in range and fill disjoint column groups."""
    today = date(2026, 7, 22)
    prev_sets = [_set(date(2026, 7, 13), "w-prev", 80.0, 8, 7.5)]
    curr_sets = [_set(date(2026, 7, 20), "w-curr", 85.0, 8, 8.0)]
    week_windows = [
        (date(2026, 7, 13), prev_sets),
        (date(2026, 7, 20), curr_sets),
    ]
    plan = plan_writes(CFG, DAILY_GRID, BLOCK_GRID, [], week_windows, today)

    values = {(w.row, w.col): w.value for w in plan.block_writes}
    # Previous week -> week-1 group (cols 3,4,5)
    assert values[(1, 3)] == "8"
    assert values[(1, 4)] == "80"
    assert values[(1, 5)] == "RPE 7.5"
    # Current week -> week-2 group (cols 7,8,9)
    assert values[(1, 7)] == "8"
    assert values[(1, 8)] == "85"
    assert values[(1, 9)] == "RPE 8"

    assert any("week 1, w/c 2026-07-13" in line for line in plan.summary_lines)
    assert any("week 2, w/c 2026-07-20" in line for line in plan.summary_lines)


def test_plan_writes_skips_out_of_range_window_but_writes_the_other():
    """today=2026-07-15 (Wed, in week 1) -> current_monday=2026-07-13 (index 0,
    in range), prev_monday=2026-07-06 (index -1, predates week1_monday)."""
    today = date(2026, 7, 15)
    curr_sets = [_set(date(2026, 7, 13), "w-curr", 85.0, 8, 8.0)]
    week_windows = [
        (date(2026, 7, 6), []),
        (date(2026, 7, 13), curr_sets),
    ]
    plan = plan_writes(CFG, DAILY_GRID, BLOCK_GRID, [], week_windows, today)

    assert any("skipped w/c 2026-07-06" in line for line in plan.summary_lines), plan.summary_lines
    values = {(w.row, w.col): w.value for w in plan.block_writes}
    assert values[(1, 3)] == "8"  # week-1 group still written
    assert values[(1, 4)] == "85"


def test_plan_writes_reports_unmapped_deduplicated_across_windows():
    grid = [row[:] for row in BLOCK_GRID]
    grid[1][0] = "MYSTERY PRESS"
    today = date(2026, 7, 22)
    week_windows = [
        (date(2026, 7, 13), []),
        (date(2026, 7, 20), []),
    ]
    plan = plan_writes(CFG, DAILY_GRID, grid, [], week_windows, today)

    unmapped_lines = [line for line in plan.summary_lines if "MYSTERY PRESS" in line]
    assert len(unmapped_lines) == 1
