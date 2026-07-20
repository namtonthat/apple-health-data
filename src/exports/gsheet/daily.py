"""Resolve cell writes for the daily tracking tab.

Pure logic: takes the tab as a grid of strings plus daily health rows,
returns pending CellWrites. Never touches the network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from exports.gsheet.model import CellWrite, DailyRow, fmt_num, is_blank

REQUIRED_HEADERS = [
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
]


@dataclass
class DailyResult:
    writes: list[CellWrite] = field(default_factory=list)
    skipped: int = 0
    notes: list[str] = field(default_factory=list)


def _find_header(grid: list[list[str]]) -> tuple[int, dict[str, int]]:
    for i, row in enumerate(grid):
        if any(c.strip().upper() == "BODY WEIGHT" for c in row):
            cols: dict[str, int] = {}
            for j, cell in enumerate(row):
                key = cell.strip().upper()
                if key and key not in cols:
                    cols[key] = j
            missing = [h for h in REQUIRED_HEADERS if h not in cols]
            if missing:
                raise ValueError(f"daily tab: missing headers {missing}")
            return i, cols
    raise ValueError("daily tab: no header row containing BODY WEIGHT")


def _parse_date(cell: str) -> date | None:
    try:
        return datetime.strptime(cell.strip(), "%d/%m/%y").date()
    except ValueError:
        return None


def _cell(grid: list[list[str]], row: int, col: int) -> str:
    if row >= len(grid) or col >= len(grid[row]):
        return ""
    return grid[row][col]


def _mean(values: list[float]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def _round_decimal(v: float, places: int) -> str:
    """Round using ROUND_HALF_UP and format with fixed decimal places."""
    d = Decimal(str(v))
    rounded = d.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)
    return f"{rounded:.{places}f}"


def _maybe_write(
    result: DailyResult, grid: list[list[str]], row: int, col: int, value: str
) -> None:
    if is_blank(_cell(grid, row, col)):
        result.writes.append(CellWrite(row=row, col=col, value=value))
    else:
        result.skipped += 1


def resolve_daily_writes(grid: list[list[str]], rows: list[DailyRow], today: date) -> DailyResult:
    header_row, cols = _find_header(grid)
    by_date = {r.date: r for r in rows}
    result = DailyResult()

    for i in range(header_row + 1, len(grid)):
        row_date = _parse_date(_cell(grid, i, cols["DATE"]))
        if row_date is None:
            continue

        if row_date < today:
            metrics = by_date.get(row_date)
            if metrics:
                if metrics.weight_kg is not None:
                    _maybe_write(
                        result, grid, i, cols["BODY WEIGHT"], _round_decimal(metrics.weight_kg, 1)
                    )
                if metrics.sleep_hours is not None:
                    _maybe_write(
                        result, grid, i, cols["TOTAL HRS"], _round_decimal(metrics.sleep_hours, 1)
                    )

        # Weekly average row sits directly below the SUN row.
        if _cell(grid, i, cols["DAY"]).strip().upper() == "SUN" and row_date < today:
            week_dates = [row_date - timedelta(days=d) for d in range(6, -1, -1)]
            week = [by_date[d] for d in week_dates if d in by_date]
            if week:
                _write_week_averages(result, grid, i + 1, cols, week)

    return result


def _write_week_averages(
    result: DailyResult,
    grid: list[list[str]],
    avg_row: int,
    cols: dict[str, int],
    week: list[DailyRow],
) -> None:
    int_metrics = {
        "CALORIES": [r.calories for r in week],
        "PROTEIN": [r.protein_g for r in week],
        "CARBS": [r.carbs_g for r in week],
        "FAT": [r.fat_g for r in week],
        "FIBRE": [r.fiber_g for r in week],
        "STEPS": [r.steps for r in week],
    }
    for header, values in int_metrics.items():
        mean = _mean(values)
        if mean is not None:
            _maybe_write(result, grid, avg_row, cols[header], fmt_num(round(mean)))

    fluid = _mean([r.water_ml for r in week])
    if fluid is not None:
        _maybe_write(result, grid, avg_row, cols["FLUID"], f"{fluid / 1000:.1f}")
