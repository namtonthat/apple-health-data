"""Health data pipelines - Extract data from various sources to S3 and transform with dbt."""
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env")
