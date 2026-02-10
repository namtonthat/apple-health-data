#!/usr/bin/env python3
"""
CLI runner for the Health & Fitness data pipeline.

Loads .env and runs individual stages or the full pipeline.

Usage:
    uv run python run.py ingest                  # All sources
    uv run python run.py ingest hevy strava      # Specific sources
    uv run python run.py transform               # dbt run
    uv run python run.py export                   # ICS calendar
    uv run python run.py all                      # Full pipeline
    uv run python run.py dashboard                # Start Streamlit
    uv run python run.py ingest --date 2026-01-15 # With extraction date
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"


def load_env() -> None:
    """Source .env into os.environ (skips comments and blank lines).

    No-op when .env is missing (e.g. CI where env vars are set externally).
    """
    import os

    if not ENV_FILE.exists():
        return

    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        if key and value:
            os.environ.setdefault(key.strip(), value.strip())


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------
INGEST_SOURCES = ["hevy", "strava", "apple-health", "openpowerlifting"]


def run_ingest(sources: list[str], date: str | None) -> None:
    """Extract data from APIs to S3 landing zone."""
    load_env()

    from pipelines.openpowerlifting import run_pipeline as run_opl
    from pipelines.pipelines.apple_health_to_s3 import run_pipeline as run_apple_health
    from pipelines.pipelines.hevy_to_s3 import run_pipeline as run_hevy
    from pipelines.pipelines.strava_to_s3 import run_pipeline as run_strava

    runners = {
        "hevy": ("Hevy", lambda: run_hevy(extraction_date=date)),
        "strava": ("Strava", lambda: run_strava(extraction_date=date)),
        "apple-health": ("Apple Health", lambda: run_apple_health(extraction_date=date)),
        "openpowerlifting": ("OpenPowerlifting", lambda: run_opl()),
    }

    for source in sources:
        if source not in runners:
            print(f"Unknown source: {source} (choose from {INGEST_SOURCES})")
            continue
        label, fn = runners[source]
        print(f"\n{'=' * 60}")
        print(f"Ingesting: {label}")
        print(f"{'=' * 60}")
        try:
            fn()
        except Exception as exc:
            print(f"Warning: {label} failed — {exc}")


def run_transform() -> None:
    """Run dbt transformations."""
    load_env()
    dbt_dir = ROOT / "dbt_project"
    print(f"\n{'=' * 60}")
    print("Running dbt transformations")
    print(f"{'=' * 60}")
    result = subprocess.run(
        ["uv", "run", "dbt", "run", "--profiles-dir", str(dbt_dir)],
        cwd=str(dbt_dir),
    )
    if result.returncode != 0:
        print("dbt run failed")
        sys.exit(result.returncode)


def run_export() -> None:
    """Export ICS calendar."""
    load_env()
    from pipelines.pipelines.export_to_ics import run_pipeline

    run_pipeline()


def run_dashboard() -> None:
    """Start the Streamlit dashboard."""
    load_env()
    home = ROOT / "src" / "dashboard" / "Home.py"
    subprocess.run(["uv", "run", "streamlit", "run", str(home)])


def run_all(date: str | None) -> None:
    """Run the full pipeline end-to-end."""
    t0 = time.time()
    print("=" * 60)
    print("Health & Fitness Pipeline — Full Run")
    print("=" * 60)

    stages = [
        ("1/3 Ingest", lambda: run_ingest(INGEST_SOURCES, date)),
        ("2/3 Transform", run_transform),
        ("3/3 Export", run_export),
    ]

    for label, fn in stages:
        print(f"\n[{label}]")
        fn()

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"All stages complete in {elapsed:.0f}s")
    print(f"{'=' * 60}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Health & Fitness Data Pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s ingest                     Run all ingestion sources
  %(prog)s ingest hevy strava         Ingest only Hevy and Strava
  %(prog)s transform                  Run dbt models
  %(prog)s export                     Export ICS calendar
  %(prog)s all                        Full pipeline end-to-end
  %(prog)s dashboard                  Start Streamlit dashboard
  %(prog)s all --date 2026-01-15      Full pipeline with custom date
""",
    )

    sub = parser.add_subparsers(dest="stage", required=True)

    # ingest
    p_ingest = sub.add_parser("ingest", help="Extract data from APIs to S3 landing zone")
    p_ingest.add_argument(
        "sources",
        nargs="*",
        default=INGEST_SOURCES,
        help=f"Sources to ingest (default: all). Choices: {', '.join(INGEST_SOURCES)}",
    )
    p_ingest.add_argument("--date", help="Extraction date (YYYY-MM-DD)", default=None)

    # transform
    sub.add_parser("transform", help="Run dbt transformations")

    # export
    sub.add_parser("export", help="Export ICS calendar to S3")

    # all
    p_all = sub.add_parser("all", help="Run full pipeline end-to-end")
    p_all.add_argument("--date", help="Extraction date (YYYY-MM-DD)", default=None)

    # dashboard
    sub.add_parser("dashboard", help="Start Streamlit dashboard")

    args = parser.parse_args()

    # Ensure src/ is on the Python path for pipeline imports
    src_dir = str(ROOT / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    match args.stage:
        case "ingest":
            run_ingest(args.sources, args.date)
        case "transform":
            run_transform()
        case "export":
            run_export()
        case "all":
            run_all(args.date)
        case "dashboard":
            run_dashboard()


if __name__ == "__main__":
    main()
