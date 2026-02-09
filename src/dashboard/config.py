"""Shared dashboard configuration loaded from pyproject.toml."""

import os
import tomllib
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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

# Goals (with defaults)
_goals_config = CONFIG.get("goals", {})
GOALS = {
    "sleep_hours": _goals_config.get("sleep_hours", 7.0),
    "sleep_deep_hours": _goals_config.get("sleep_deep_hours", 1.5),
    "sleep_rem_hours": _goals_config.get("sleep_rem_hours", 1.5),
    "sleep_light_hours": _goals_config.get("sleep_light_hours", 3.5),
    "protein_g": _goals_config.get("protein_g", 170.0),
    "carbs_g": _goals_config.get("carbs_g", 300.0),
    "fat_g": _goals_config.get("fat_g", 60.0),
    "steps": _goals_config.get("steps", 10000),
}


# Last updated timestamp (written by GitHub Actions workflow)
_last_updated_path = Path(__file__).parent.parent.parent / "last_updated.txt"
try:
    LAST_UPDATED = _last_updated_path.read_text().strip()
except FileNotFoundError:
    LAST_UPDATED = "Unknown"


TIMEZONE = ZoneInfo(CONFIG.get("timezone", "Australia/Melbourne"))


def today_local() -> date:
    """Return today's date in the configured timezone."""
    return datetime.now(TIMEZONE).date()


def get_secret(key: str, default: str = "") -> str:
    """Get secret from Streamlit Cloud secrets or env vars (local)."""
    try:
        import streamlit as st

        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.environ.get(key, default)
