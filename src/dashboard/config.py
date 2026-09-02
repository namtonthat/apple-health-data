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


TIMEZONE = ZoneInfo(CONFIG.get("timezone", "Australia/Melbourne"))


@st.cache_data(ttl=60, show_spinner=False)
def get_last_updated() -> str:
    """LastModified of the daily-summary parquet in S3, as a Melbourne timestamp.

    Callers use this as the cache-busting key for data loaders. It must come from
    S3, not a file in the repo: last_updated.txt is baked into the Docker image at
    build time and never changes in the running container, so a file-based key
    would never invalidate the cache.
    """
    import s3fs

    try:
        fs = s3fs.S3FileSystem(
            key=get_secret("AWS_ACCESS_KEY_ID"),
            secret=get_secret("AWS_SECRET_ACCESS_KEY"),
            client_kwargs={"region_name": AWS_REGION},
            skip_instance_cache=True,
        )
        modified = fs.info(f"{S3_BUCKET}/{S3_TRANSFORMED_PREFIX}/fct_daily_summary")["LastModified"]
        return modified.astimezone(TIMEZONE).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "Unknown"


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
