"""Orchestrate the Google Sheets program export."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from exports.gsheet.block import current_week_index, resolve_block_writes
from exports.gsheet.config import ExportConfig, load_config
from exports.gsheet.daily import resolve_daily_writes
from exports.gsheet.model import CellWrite, DailyRow, SetRow

DEFAULT_CONFIG = Path(__file__).resolve().parents[3] / "config" / "gsheet_export.yaml"
MELBOURNE = ZoneInfo("Australia/Melbourne")


@dataclass
class ExportPlan:
    daily_writes: list[CellWrite] = field(default_factory=list)
    block_writes: list[CellWrite] = field(default_factory=list)
    summary_lines: list[str] = field(default_factory=list)


def apply_week_overrides(
    week_windows: list[tuple[date, list[SetRow]]],
    overrides: dict[date, date],
) -> tuple[list[tuple[date, list[SetRow]]], list[str]]:
    """Reassign each overridden workout date's sets to its target week's window.

    Sets whose target week isn't among the loaded windows are dropped — that
    window was written in an earlier run, and dropping stops the delayed
    workout from also claiming an occurrence in its calendar week.
    """
    if not overrides:
        return week_windows, []

    buckets: dict[date, list[SetRow]] = {monday: [] for monday, _ in week_windows}
    moved: dict[tuple[date, date], int] = {}
    dropped: dict[tuple[date, date], int] = {}
    for monday, sets in week_windows:
        for s in sets:
            target = overrides.get(s.workout_date, monday)
            if target == monday:
                buckets[monday].append(s)
            elif target in buckets:
                buckets[target].append(s)
                moved[(s.workout_date, target)] = moved.get((s.workout_date, target), 0) + 1
            else:
                dropped[(s.workout_date, target)] = dropped.get((s.workout_date, target), 0) + 1

    notes = [
        f"week override: {n} sets from {d} reassigned to w/c {t}" for (d, t), n in moved.items()
    ] + [
        f"week override: {n} sets from {d} dropped (w/c {t} not in this run's windows)"
        for (d, t), n in dropped.items()
    ]
    return [(monday, buckets[monday]) for monday, _ in week_windows], notes


def plan_writes(
    cfg: ExportConfig,
    daily_grid: list[list[str]],
    block_grid: list[list[str]],
    daily_rows: list[DailyRow],
    week_windows: list[tuple[date, list[SetRow]]],
    today: date,
) -> ExportPlan:
    plan = ExportPlan()
    week_windows, override_notes = apply_week_overrides(week_windows, cfg.week_overrides)
    plan.summary_lines.extend(f"block tab: {note}" for note in override_notes)

    daily = resolve_daily_writes(daily_grid, daily_rows, today)
    plan.daily_writes = daily.writes
    plan.summary_lines.append(
        f"daily tab: {len(daily.writes)} cells written, {daily.skipped} already filled"
    )
    plan.summary_lines.extend(f"daily tab: {note}" for note in daily.notes)

    unmapped: dict[str, None] = {}
    for monday, sets in week_windows:
        week_index = current_week_index(cfg.week1_monday, monday)
        try:
            block = resolve_block_writes(block_grid, cfg.exercise_map, week_index, sets)
        except ValueError as exc:
            plan.summary_lines.append(f"block tab: skipped w/c {monday.isoformat()} — {exc}")
            continue

        plan.block_writes.extend(block.writes)
        plan.summary_lines.append(
            f"block tab (week {week_index + 1}, w/c {monday.isoformat()}): "
            f"{len(block.writes)} cells written ({block.replaced} replaced), "
            f"{block.skipped} already correct"
        )
        for name in block.unmapped:
            unmapped.setdefault(name)
        plan.summary_lines.extend(f"block tab: {note}" for note in block.notes)

    if unmapped:
        plan.summary_lines.append(
            "block tab: unmapped movements (add to config/gsheet_export.yaml): "
            + ", ".join(unmapped)
        )
    return plan


def run_export_sheet(
    config_path: Path = DEFAULT_CONFIG, dry_run: bool = False, list_tabs: bool = False
) -> None:
    from exports.gsheet.sheet import SheetClient, a1

    cfg = load_config(config_path)

    sa_json = os.environ.get("GSHEET_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        raise SystemExit(
            "GSHEET_SERVICE_ACCOUNT_JSON is not set. Add the service account "
            "JSON (single line) to .env or the CI secret."
        )
    client = SheetClient(cfg.spreadsheet_id, sa_json)

    if list_tabs:
        print("Tabs in spreadsheet:")
        for title in client.list_tabs():
            print(f"  - {title}")
        return

    if not cfg.daily_tab or not cfg.block_tab:
        raise SystemExit(
            "daily_tab / block.tab not set in config/gsheet_export.yaml — "
            "run with --list-tabs and fill them in."
        )

    from exports.gsheet.data import load_daily_rows, load_week_sets
    from pipelines.config import get_duckdb_connection

    today = datetime.now(MELBOURNE).date()
    # The block tab covers two windows each run: the previous completed
    # Mon-Sun week (which may have gained late-logged sets) and the current
    # in-progress week (so sets show up as they're logged mid-week). They
    # fill disjoint week-group columns, so writing both is safe and
    # idempotent.
    current_monday = today - timedelta(days=today.weekday())
    prev_monday = current_monday - timedelta(days=7)

    conn = get_duckdb_connection()
    daily_rows = load_daily_rows(conn)
    prev_sets = load_week_sets(conn, prev_monday)
    curr_sets = load_week_sets(conn, current_monday)
    week_windows = [(prev_monday, prev_sets), (current_monday, curr_sets)]

    daily_grid = client.get_grid(cfg.daily_tab)
    block_grid = client.get_grid(cfg.block_tab)

    plan = plan_writes(cfg, daily_grid, block_grid, daily_rows, week_windows, today)

    print("=" * 60)
    print(f"Google Sheets Program Export{' (DRY RUN)' if dry_run else ''}")
    print("=" * 60)
    for tab, writes in ((cfg.daily_tab, plan.daily_writes), (cfg.block_tab, plan.block_writes)):
        for w in writes:
            print(f"  {tab}!{a1(w.row, w.col)}: {w.value}")

    if not dry_run:
        client.batch_write(cfg.daily_tab, plan.daily_writes)
        client.batch_write(cfg.block_tab, plan.block_writes)

    print("\nSummary:")
    for line in plan.summary_lines:
        print(f"  {line}")
    if dry_run:
        print("  DRY RUN — nothing was written.")
