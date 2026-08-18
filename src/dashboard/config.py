"""Shared dashboard configuration loaded from pyproject.toml."""

import os
import tomllib
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
from dotenv import load_dotenv

# Load .env for local development (AWS creds, etc.)
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Load non-sensitive config from pyproject.toml
_pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
with open(_pyproject_path, "rb") as _f:
    _pyproject = tomllib.load(_f)
CONFIG = _pyproject.get("tool", {}).get("dashboard", {})

# S3 configuration
S3_BUCKET = CONFIG.get("s3_bucket_name", "")
S3_TRANSFORMED_PREFIX = CONFIG.get("s3_transformed_prefix", "transformed")
AWS_REGION = CONFIG.get("aws_region", "ap-southeast-2")

# User info
USER_NAME = CONFIG.get("user_name", "there")
OPENPOWERLIFTING_URL = CONFIG.get("openpowerlifting_url", "")

# Goals -- pyproject.toml [tool.dashboard.goals] always defines these keys, so no
# in-code fallback defaults (they can only drift out of sync with the TOML, as
# happened here previously).
_goals_config = CONFIG.get("goals", {})
GOALS = {
    "sleep_hours": _goals_config["sleep_hours"],
    "sleep_deep_hours": _goals_config["sleep_deep_hours"],
    "sleep_rem_hours": _goals_config["sleep_rem_hours"],
    "sleep_light_hours": _goals_config["sleep_light_hours"],
    "protein_g": _goals_config["protein_g"],
    "carbs_g": _goals_config["carbs_g"],
    "fat_g": _goals_config["fat_g"],
    "weight_kg": _goals_config["weight_kg"],
    "resting_hr_bpm": _goals_config["resting_hr_bpm"],
    "hrv_ms": _goals_config["hrv_ms"],
    "vo2_max": _goals_config["vo2_max"],
    "steps": _goals_config["steps"],
    "meditation_minutes": _goals_config["meditation_minutes"],
}
GOALS["calories"] = GOALS["protein_g"] * 4 + GOALS["carbs_g"] * 4 + GOALS["fat_g"] * 9


_last_updated_path = Path(__file__).parent.parent.parent / "last_updated.txt"


def get_last_updated() -> str:
    """Read last_updated.txt fresh (written daily by the CI refresh workflow).

    A cheap few-byte file read -- callers use this as a cache-busting key so
    ``st.cache_data`` loaders invalidate exactly when new data lands, rather than
    on a wall-clock TTL that doesn't match the once-daily refresh cadence.
    """
    try:
        return _last_updated_path.read_text().strip()
    except FileNotFoundError:
        return "Unknown"


# Last updated timestamp for display (Home.py); computed once at import.
LAST_UPDATED = get_last_updated()


TIMEZONE = ZoneInfo(CONFIG.get("timezone", "Australia/Melbourne"))


def today_local() -> date:
    """Return today's date in the configured timezone."""
    return datetime.now(TIMEZONE).date()


def get_secret(key: str, default: str = "") -> str:
    """Get secret from Streamlit Cloud secrets or env vars (local).

    ``st.secrets`` (~/.streamlit/secrets.toml or Streamlit Cloud secrets) takes
    precedence over `.env` / process environment variables.
    """
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.environ.get(key, default)
