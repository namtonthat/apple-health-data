from datetime import date
from pathlib import Path

import pytest

from exports.gsheet.config import load_config

SAMPLE = """\
spreadsheet_id: abc123
daily_tab: "Daily"
block:
  tab: "Block ESS"
  week1_monday: 2026-07-13
exercise_map:
  comp bench: Bench Press (Barbell)
  LOW BAR SQUAT: Squat (Barbell)
"""


def write_config(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "gsheet_export.yaml"
    p.write_text(text)
    return p


def test_load_config_parses_fields(tmp_path):
    cfg = load_config(write_config(tmp_path, SAMPLE))
    assert cfg.spreadsheet_id == "abc123"
    assert cfg.daily_tab == "Daily"
    assert cfg.block_tab == "Block ESS"
    assert cfg.week1_monday == date(2026, 7, 13)


def test_load_config_normalises_exercise_map_keys(tmp_path):
    cfg = load_config(write_config(tmp_path, SAMPLE))
    assert cfg.exercise_map == {
        "COMP BENCH": "Bench Press (Barbell)",
        "LOW BAR SQUAT": "Squat (Barbell)",
    }


def test_load_config_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.yaml")


def test_load_config_missing_key_raises(tmp_path):
    with pytest.raises(ValueError, match="spreadsheet_id"):
        load_config(write_config(tmp_path, "daily_tab: x\n"))
