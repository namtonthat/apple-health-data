from datetime import date

import pytest

from exports.gsheet.block import current_week_index, resolve_block_writes
from exports.gsheet.model import SetRow

# Header layout: col 2 MOVEMENT, col 3 SETSxREPS, then 2 week groups of
# TARGET/REPS/LOAD/ACTUAL, then a right-hand panel MOVEMENT (taper) to stop at.
HEADER = [
    "",
    "",
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
    "MOVEMENT",
    "SETSxREPS",
    "TARGET",
    "REPS",
    "LOAD",
    "ACTUAL",
]
N = len(HEADER)


def ex_row(movement: str, sets_reps: str = "3x5") -> list[str]:
    """An anchor row: MOVEMENT + SETSxREPS both filled."""
    row = [""] * N
    row[2], row[3] = movement, sets_reps
    row[7] = row[11] = "RATE"  # unfilled ACTUAL placeholder
    return row


def cont_row(target_wk1: str = "", note: str = "") -> list[str]:
    """A continuation row: no SETSxREPS. Optionally a lowercase coach note in
    the MOVEMENT column, and/or a week-1 TARGET value."""
    row = [""] * N
    if note:
        row[2] = note
    row[4] = target_wk1
    row[7] = row[11] = "RATE"
    return row


def make_grid() -> list[list[str]]:
    return [
        ["", "", "BLOCK", "ESS"] + [""] * (N - 4),
        HEADER[:],
        ex_row("COMP BENCH", "3x5-8"),
        ex_row("LOW BAR SQUAT", "1x1"),
        [""] * N,  # spacer
        ex_row("LOW BAR SQUAT", "1x1"),  # same movement, later day
        ["", "", "NOTES:", ""] + [""] * (N - 4),
    ]


def s(
    day: int, ex: str, num: int, kg: float, reps: int, rpe: float | None, wid: str = ""
) -> SetRow:
    return SetRow(
        workout_id=wid or f"w{day}",
        workout_date=date(2026, 7, 13 + day),
        exercise_name=ex,
        set_number=num,
        weight_kg=kg,
        reps=reps,
        rpe=rpe,
    )


EXERCISE_MAP = {
    "COMP BENCH": "Bench Press (Barbell)",
    "LOW BAR SQUAT": "Squat (Barbell)",
    "HIGH BAR SQUAT": "Squat (Barbell)",
}


def test_current_week_index():
    monday = date(2026, 7, 13)
    assert current_week_index(monday, date(2026, 7, 13)) == 0
    assert current_week_index(monday, date(2026, 7, 19)) == 0
    assert current_week_index(monday, date(2026, 7, 20)) == 1
    assert current_week_index(monday, date(2026, 7, 12)) < 0


def test_writes_top_set_into_selected_week_group():
    sets = [
        s(0, "Bench Press (Barbell)", 1, 80.0, 8, 7.0),
        s(0, "Bench Press (Barbell)", 2, 82.5, 8, 7.5),
    ]
    result = resolve_block_writes(make_grid(), EXERCISE_MAP, 1, sets)
    values = {(w.row, w.col): w.value for w in result.writes}
    assert values[(2, 9)] == "8"  # REPS in week-2 group
    assert values[(2, 10)] == "82.5"  # LOAD
    assert values[(2, 11)] == "RPE 7.5"  # ACTUAL (RATE treated as blank)


def test_second_occurrence_uses_second_workout():
    sets = [
        s(0, "Squat (Barbell)", 1, 150.0, 1, 6.0),
        s(4, "Squat (Barbell)", 1, 160.0, 1, 8.0),
    ]
    result = resolve_block_writes(make_grid(), EXERCISE_MAP, 0, sets)
    values = {(w.row, w.col): w.value for w in result.writes}
    assert values[(3, 6)] == "150"  # first occurrence -> first workout
    assert values[(5, 6)] == "160"  # second occurrence -> second workout


def test_unmapped_movement_reported_not_written():
    grid = make_grid()
    grid[2][2] = "MYSTERY PRESS"
    result = resolve_block_writes(grid, EXERCISE_MAP, 0, [])
    assert "MYSTERY PRESS" in result.unmapped
    assert all(w.row != 2 for w in result.writes)


def test_filled_cells_are_skipped():
    grid = make_grid()
    grid[2][9] = "8"  # REPS already filled
    sets = [s(0, "Bench Press (Barbell)", 1, 80.0, 8, None)]
    result = resolve_block_writes(grid, EXERCISE_MAP, 1, sets)
    assert (2, 9) not in {(w.row, w.col) for w in result.writes}
    assert result.skipped >= 1


def test_no_rpe_leaves_actual_untouched():
    sets = [s(0, "Bench Press (Barbell)", 1, 80.0, 8, None)]
    result = resolve_block_writes(make_grid(), EXERCISE_MAP, 1, sets)
    cols = {w.col for w in result.writes if w.row == 2}
    assert cols == {9, 10}  # REPS + LOAD only


def test_week_index_out_of_range_raises():
    with pytest.raises(ValueError, match="week"):
        resolve_block_writes(make_grid(), EXERCISE_MAP, 2, [])


def test_occurrence_keyed_by_hevy_exercise_not_sheet_movement():
    """COMP BENCH and COMP PRESS are different sheet movements that both alias
    to 'Bench Press (Barbell)' in Hevy. With two workouts logged that week,
    the first sheet row (COMP BENCH) should get workout 1's top set and the
    second sheet row (COMP PRESS) should get workout 2's top set — not both
    landing on workout 1 because each sheet movement's own occurrence
    counter starts fresh at 0."""
    grid = make_grid()
    grid[2][2] = "COMP BENCH"
    grid[3][2] = "COMP PRESS"
    exercise_map = {
        "COMP BENCH": "Bench Press (Barbell)",
        "COMP PRESS": "Bench Press (Barbell)",
    }
    sets = [
        s(0, "Bench Press (Barbell)", 1, 80.0, 8, 7.0),
        s(4, "Bench Press (Barbell)", 1, 90.0, 8, 8.0),
    ]
    result = resolve_block_writes(grid, exercise_map, 0, sets)
    values = {(w.row, w.col): w.value for w in result.writes}
    assert values[(2, 6)] == "80"  # COMP BENCH row -> first workout
    assert values[(3, 6)] == "90"  # COMP PRESS row -> second workout


def test_invalid_set_workout_skipped_not_shifted():
    """First workout has no valid sets; second row should still get second workout."""
    sets = [
        s(0, "Squat (Barbell)", 1, None, 1, 6.0),  # First workout: invalid (no weight)
        s(4, "Squat (Barbell)", 1, 160.0, 1, 8.0),  # Second workout: valid
    ]
    result = resolve_block_writes(make_grid(), EXERCISE_MAP, 0, sets)
    values = {(w.row, w.col): w.value for w in result.writes}
    # First row (row 3) should have no writes (first workout has no valid sets)
    assert all(w.row != 3 for w in result.writes)
    # Second row (row 5) should get the second workout's load
    assert values[(5, 6)] == "160"
    # First occurrence should be in notes as having no loggable sets
    assert any("no loggable sets" in note for note in result.notes)


def test_block15_style_per_set_rows():
    """Anchor 'HIGH BAR SQUAT' 3x5 followed by 2 continuation rows with
    real week-1 targets ('RIR 4+') and 2 unused continuation rows ('-'
    targets). Three logged sets of differing weight/set_number should land
    set 1 on the anchor row and sets 2-3 on the two active continuation
    rows; the '-' rows must stay untouched."""
    grid = [
        ["", "", "BLOCK", "ESS"] + [""] * (N - 4),
        HEADER[:],
        ex_row("HIGH BAR SQUAT", "3x5"),  # anchor, row 2
        cont_row(target_wk1="RIR 4+"),  # active continuation, row 3
        cont_row(target_wk1="RIR 4+"),  # active continuation, row 4
        cont_row(target_wk1="-"),  # unused, row 5
        cont_row(target_wk1="-"),  # unused, row 6
        ["", "", "NOTES:", ""] + [""] * (N - 4),
    ]
    sets = [
        s(0, "Squat (Barbell)", 1, 100.0, 5, 7.0),
        s(0, "Squat (Barbell)", 2, 105.0, 5, 7.5),
        s(0, "Squat (Barbell)", 3, 110.0, 5, 8.0),
    ]
    result = resolve_block_writes(grid, EXERCISE_MAP, 0, sets)
    values = {(w.row, w.col): w.value for w in result.writes}
    assert values[(2, 6)] == "100"  # set 1 -> anchor row LOAD (week-1 group)
    assert values[(3, 6)] == "105"  # set 2 -> first active continuation row
    assert values[(4, 6)] == "110"  # set 3 -> second active continuation row
    assert all(w.row not in (5, 6) for w in result.writes)  # '-' rows untouched


def test_lowercase_note_continuation_row_is_active_not_unmapped():
    """A lowercase coach note ('touch and go') with no SETSxREPS but a real
    target value is a continuation row of the anchor above: it should be
    treated as active (and thus eligible to receive a set) and must never
    show up in `unmapped`."""
    grid = [
        ["", "", "BLOCK", "ESS"] + [""] * (N - 4),
        HEADER[:],
        ex_row("HIGH BAR SQUAT", "3x5"),  # anchor, row 2
        cont_row(target_wk1="RIR 4+", note="touch and go"),  # active, row 3
        ["", "", "NOTES:", ""] + [""] * (N - 4),
    ]
    sets = [
        s(0, "Squat (Barbell)", 1, 100.0, 5, 7.0),
        s(0, "Squat (Barbell)", 2, 105.0, 5, 7.5),
    ]
    result = resolve_block_writes(grid, EXERCISE_MAP, 0, sets)
    values = {(w.row, w.col): w.value for w in result.writes}
    assert values[(2, 6)] == "100"
    assert values[(3, 6)] == "105"
    assert "touch and go" not in result.unmapped
    assert not any("touch and go" in u for u in result.unmapped)
