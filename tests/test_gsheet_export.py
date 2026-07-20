from datetime import date

from exports.gsheet.config import ExportConfig
from exports.gsheet.export import plan_writes
from exports.gsheet.model import DailyRow, SetRow

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

BLOCK_GRID = [
    ["MOVEMENT", "SETSxREPS", "TARGET", "REPS", "LOAD", "ACTUAL"],
    ["COMP BENCH", "3x5", "RPE 7", "", "", "RATE"],
]


def test_plan_writes_produces_both_sections():
    daily_rows = [
        DailyRow(
            date=date(2026, 7, 13),
            weight_kg=70.3,
            sleep_hours=7.2,
            calories=None,
            protein_g=None,
            carbs_g=None,
            fat_g=None,
            fiber_g=None,
            water_ml=None,
            steps=None,
        )
    ]
    sets = [
        SetRow(
            workout_id="w1",
            workout_date=date(2026, 7, 13),
            exercise_name="Bench Press (Barbell)",
            set_number=1,
            weight_kg=80.0,
            reps=8,
            rpe=7.5,
        )
    ]
    plan = plan_writes(CFG, DAILY_GRID, BLOCK_GRID, daily_rows, sets, today=date(2026, 7, 15))
    assert len(plan.daily_writes) == 2  # weight + sleep
    assert len(plan.block_writes) == 3  # reps + load + actual
    assert any("written" in line for line in plan.summary_lines)


def test_plan_writes_skips_block_when_before_block_start():
    plan = plan_writes(CFG, DAILY_GRID, BLOCK_GRID, [], [], today=date(2026, 7, 10))
    assert plan.block_writes == []
    assert any("skip" in line.lower() for line in plan.summary_lines)


def test_plan_writes_reports_unmapped():
    grid = [row[:] for row in BLOCK_GRID]
    grid[1][0] = "MYSTERY PRESS"
    plan = plan_writes(CFG, DAILY_GRID, grid, [], [], today=date(2026, 7, 15))
    assert any("MYSTERY PRESS" in line for line in plan.summary_lines)
