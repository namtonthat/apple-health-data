"""dlt sources for data extraction."""
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env")

from .apple_health import apple_health_source
from .hevy import hevy_source

__all__ = ["hevy_source", "apple_health_source"]
