"""Resolve cell writes for the current training-block tab.

Pure logic: takes the tab as a grid of strings, the movement->Hevy exercise
map, the active week column-group index, and the week's working sets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from exports.gsheet.model import CellWrite, SetRow, fmt_num, is_blank

GROUP_HEADERS = ("TARGET", "REPS", "LOAD", "ACTUAL")


@dataclass(frozen=True)
class WeekGroup:
    reps_col: int
    load_col: int
    actual_col: int


@dataclass
class BlockResult:
    writes: list[CellWrite] = field(default_factory=list)
    skipped: int = 0
    unmapped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def current_week_index(week1_monday: date, today: date) -> int:
    """0-based week group for today; negative before the block starts."""
    return (today - week1_monday).days // 7


def _find_layout(grid: list[list[str]]) -> tuple[int, int, list[WeekGroup]]:
    """Locate the header row, the main MOVEMENT column, and the week groups."""
    for i, row in enumerate(grid):
        upper = [c.strip().upper() for c in row]
        if "MOVEMENT" in upper and "SETSXREPS" in upper:
            movement_cols = [j for j, c in enumerate(upper) if c == "MOVEMENT"]
            start = movement_cols[0]
            stop = movement_cols[1] if len(movement_cols) > 1 else len(upper)
            groups = []
            j = start
            while j + 3 < stop:
                if tuple(upper[j : j + 4]) == GROUP_HEADERS:
                    groups.append(WeekGroup(reps_col=j + 1, load_col=j + 2, actual_col=j + 3))
                    j += 4
                else:
                    j += 1
            if not groups:
                raise ValueError("block tab: no TARGET/REPS/LOAD/ACTUAL week groups found")
            return i, start, groups
    raise ValueError("block tab: no header row with MOVEMENT and SETSxREPS")


def _cell(grid: list[list[str]], row: int, col: int) -> str:
    if row >= len(grid) or col >= len(grid[row]):
        return ""
    return grid[row][col]


def _movement_runs(
    grid: list[list[str]], header_row: int, movement_col: int
) -> list[tuple[str, list[int]]]:
    """Group consecutive same-movement rows into runs of grid row indices."""
    runs: list[tuple[str, list[int]]] = []
    for i in range(header_row + 1, len(grid)):
        name = _cell(grid, i, movement_col).strip()
        if not name or name.upper().startswith("NOTES"):
            continue
        if runs and runs[-1][0].upper() == name.upper() and runs[-1][1][-1] == i - 1:
            runs[-1][1].append(i)
        else:
            runs.append((name, [i]))
    return runs


def _workouts_for(sets: list[SetRow], exercise: str) -> list[list[SetRow]]:
    """The week's workouts containing `exercise`, each as its sets, date order."""
    by_workout: dict[str, list[SetRow]] = {}
    for s in sets:
        if s.exercise_name == exercise and s.weight_kg is not None and s.reps:
            by_workout.setdefault(s.workout_id, []).append(s)
    workouts = sorted(by_workout.values(), key=lambda ws: (ws[0].workout_date, ws[0].workout_id))
    return [sorted(ws, key=lambda s: s.set_number) for ws in workouts]


def _maybe_write(
    result: BlockResult, grid: list[list[str]], row: int, col: int, value: str
) -> None:
    if is_blank(_cell(grid, row, col)):
        result.writes.append(CellWrite(row=row, col=col, value=value))
    else:
        result.skipped += 1


def _write_set(
    result: BlockResult, grid: list[list[str]], row: int, group: WeekGroup, s: SetRow
) -> None:
    _maybe_write(result, grid, row, group.reps_col, str(int(s.reps)))
    _maybe_write(result, grid, row, group.load_col, fmt_num(s.weight_kg))
    if s.rpe is not None:
        _maybe_write(result, grid, row, group.actual_col, f"RPE {fmt_num(s.rpe)}")


def resolve_block_writes(
    grid: list[list[str]],
    exercise_map: dict[str, str],
    week_index: int,
    sets: list[SetRow],
) -> BlockResult:
    header_row, movement_col, groups = _find_layout(grid)
    if not 0 <= week_index < len(groups):
        raise ValueError(f"week index {week_index} outside the tab's {len(groups)} week groups")
    group = groups[week_index]

    result = BlockResult()
    occurrence: dict[str, int] = {}

    for name, rows in _movement_runs(grid, header_row, movement_col):
        key = name.upper()
        hevy_name = exercise_map.get(key)
        if hevy_name is None:
            if name not in result.unmapped:
                result.unmapped.append(name)
            continue

        occ = occurrence.get(key, 0)
        occurrence[key] = occ + 1
        workouts = _workouts_for(sets, hevy_name)
        if occ >= len(workouts):
            result.notes.append(f"{name}: no workout for occurrence {occ + 1} this week")
            continue
        workout = workouts[occ]

        if len(rows) == 1:
            top = max(workout, key=lambda s: (s.weight_kg, s.reps))
            _write_set(result, grid, rows[0], group, top)
        else:
            for j, row in enumerate(rows):
                if j < len(workout):
                    _write_set(result, grid, row, group, workout[j])

    return result
