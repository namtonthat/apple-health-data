"""Load and validate the gsheet export YAML config."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ExportConfig:
    spreadsheet_id: str
    daily_tab: str
    block_tab: str
    week1_monday: date
    exercise_map: dict[str, str]


def load_config(path: Path) -> ExportConfig:
    raw = yaml.safe_load(path.read_text())

    try:
        spreadsheet_id = raw["spreadsheet_id"]
        daily_tab = raw["daily_tab"]
        block = raw["block"]
        block_tab = block["tab"]
        week1_monday = block["week1_monday"]
        exercise_map = raw.get("exercise_map") or {}
    except (KeyError, TypeError) as exc:
        raise ValueError(f"gsheet_export.yaml missing required key: {exc}") from exc

    if not isinstance(week1_monday, date):
        week1_monday = date.fromisoformat(str(week1_monday))

    return ExportConfig(
        spreadsheet_id=str(spreadsheet_id),
        daily_tab=str(daily_tab),
        block_tab=str(block_tab),
        week1_monday=week1_monday,
        exercise_map={str(k).strip().upper(): str(v).strip() for k, v in exercise_map.items()},
    )
