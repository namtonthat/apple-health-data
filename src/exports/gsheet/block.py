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
    target_col: int
    reps_col: int
    load_col: int
    actual_col: int


@dataclass
class BlockResult:
    writes: list[CellWrite] = field(default_factory=list)
    skipped: int = 0
    unmapped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class _Run:
    """An exercise anchor row plus its following continuation rows."""

    name: str
    anchor_row: int
    rows: list[int]


def current_week_index(week1_monday: date, today: date) -> int:
    """0-based week group for today; negative before the block starts."""
    return (today - week1_monday).days // 7


def _find_layout(grid: list[list[str]]) -> tuple[int, int, int, list[WeekGroup]]:
    """Locate the header row, MOVEMENT column, SETSxREPS column, and week groups."""
    for i, row in enumerate(grid):
        upper = [c.strip().upper() for c in row]
        if "MOVEMENT" in upper and "SETSXREPS" in upper:
            movement_cols = [j for j, c in enumerate(upper) if c == "MOVEMENT"]
            start = movement_cols[0]
            stop = movement_cols[1] if len(movement_cols) > 1 else len(upper)
            if start + 1 >= len(upper) or upper[start + 1] != "SETSXREPS":
                raise ValueError("block tab: SETSxREPS column must follow MOVEMENT")
            setsxreps_col = start + 1
            groups = []
            j = start
            while j + 3 < stop:
                if tuple(upper[j : j + 4]) == GROUP_HEADERS:
                    groups.append(
                        WeekGroup(target_col=j, reps_col=j + 1, load_col=j + 2, actual_col=j + 3)
                    )
                    j += 4
                else:
                    j += 1
            if not groups:
                raise ValueError("block tab: no TARGET/REPS/LOAD/ACTUAL week groups found")
            return i, start, setsxreps_col, groups
    raise ValueError("block tab: no header row with MOVEMENT and SETSxREPS")


def _cell(grid: list[list[str]], row: int, col: int) -> str:
    if row >= len(grid) or col >= len(grid[row]):
        return ""
    return grid[row][col]


def _movement_runs(
    grid: list[list[str]], header_row: int, movement_col: int, setsxreps_col: int
) -> list[_Run]:
    """Group anchor rows with their trailing continuation rows into runs.

    An anchor row has a non-empty MOVEMENT cell (not starting with "NOTES")
    and a non-empty SETSxREPS cell. A run is the anchor plus every following
    row up to (exclusive) the next anchor row or a "NOTES" row. Rows before
    the first anchor are ignored.
    """
    runs: list[_Run] = []
    current: _Run | None = None
    for i in range(header_row + 1, len(grid)):
        name = _cell(grid, i, movement_col).strip()
        is_notes = name.upper().startswith("NOTES")
        if is_notes:
            current = None
            continue

        is_anchor = bool(name) and bool(_cell(grid, i, setsxreps_col).strip())
        if is_anchor:
            current = _Run(name=name, anchor_row=i, rows=[i])
            runs.append(current)
        elif current is not None:
            current.rows.append(i)
        # else: continuation row before any anchor — ignored.
    return runs


def _active_rows(grid: list[list[str]], run: _Run, group: WeekGroup) -> list[int]:
    """Rows in the run that should receive a set for the selected week group.

    The anchor row is always active. A continuation row is active iff its
    TARGET cell in the selected group is non-empty (after strip) and not "-".
    """
    active = [run.anchor_row]
    for row in run.rows[1:]:
        target = _cell(grid, row, group.target_col).strip()
        if target and target != "-":
            active.append(row)
    return active


def _workouts_for(sets: list[SetRow], exercise: str) -> list[list[SetRow]]:
    """The week's workouts containing `exercise`, each as its sets, date order."""
    by_workout: dict[str, list[SetRow]] = {}
    for s in sets:
        if s.exercise_name == exercise:
            by_workout.setdefault(s.workout_id, []).append(s)
    workouts = sorted(by_workout.values(), key=lambda ws: (ws[0].workout_date, ws[0].workout_id))
    # Filter to valid sets (weight_kg and reps) within each workout
    return [
        sorted([s for s in ws if s.weight_kg is not None and s.reps], key=lambda s: s.set_number)
        for ws in workouts
    ]


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
    header_row, movement_col, setsxreps_col, groups = _find_layout(grid)
    if not 0 <= week_index < len(groups):
        raise ValueError(f"week index {week_index} outside the tab's {len(groups)} week groups")
    group = groups[week_index]

    result = BlockResult()
    occurrence: dict[str, int] = {}

    for run in _movement_runs(grid, header_row, movement_col, setsxreps_col):
        name = run.name
        key = name.upper()
        hevy_name = exercise_map.get(key)
        if hevy_name is None:
            if name not in result.unmapped:
                result.unmapped.append(name)
            continue

        occ = occurrence.get(hevy_name, 0)
        occurrence[hevy_name] = occ + 1
        workouts = _workouts_for(sets, hevy_name)
        if occ >= len(workouts):
            result.notes.append(f"{name}: no workout for occurrence {occ + 1} this week")
            continue
        workout = workouts[occ]

        if not workout:
            result.notes.append(f"{name}: no loggable sets for occurrence {occ + 1} this week")
            continue

        active_rows = _active_rows(grid, run, group)
        if len(active_rows) == 1:
            top = max(workout, key=lambda s: (s.weight_kg, s.reps))
            _write_set(result, grid, active_rows[0], group, top)
        else:
            for j, row in enumerate(active_rows):
                if j < len(workout):
                    _write_set(result, grid, row, group, workout[j])

    return result
