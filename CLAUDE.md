# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal health and fitness analytics platform that extracts data from Apple Health, Hevy, Strava, and OpenPowerlifting, transforms it through a two-layer architecture (landing → transformed), and serves it via a Streamlit dashboard.

## Common Commands

```bash
# Install dependencies
./scripts/setup.sh

# Run full pipeline (ingest → transform → export)
uv run python run.py all

# Individual pipeline stages
uv run python run.py ingest                    # All sources to S3 landing
uv run python run.py ingest hevy strava        # Specific sources
uv run python run.py ingest --date 2026-01-15  # Custom date
uv run python run.py transform                 # dbt models
uv run python run.py export                    # ICS calendar export

# Start dashboard
uv run python run.py dashboard

# Linting
uv run ruff check --fix .                      # Python lint + autofix
uv run ruff format .                           # Python format
uv run sqlfluff lint dbt_project/models/       # SQL lint (DuckDB dialect)

# Testing
uv run pytest

# dbt (run from dbt_project/)
uv run dbt run --profiles-dir .
uv run dbt test --profiles-dir .
```

## Architecture

### Data Flow

```
Sources (APIs/files) → Landing (S3 Delta tables) → Transformed (dbt/DuckDB → S3 parquet) → Dashboard/ICS
```

### Key Modules

- **`run.py`** — CLI entry point; dispatches to pipeline stages, loads `.env` automatically
- **`src/pipelines/config.py`** — Shared utilities: S3 client, DuckDB connection (with `CREATE SECRET` for Delta), dlt destination (`table_format="delta"`)
- **`src/pipelines/sources/`** — Data source extractors (dlt sources for Hevy/Strava, JSON parser for Apple Health)
- **`src/pipelines/pipelines/`** — Pipeline runners: `*_to_s3.py` (ingest to Delta tables), `export_to_ics.py`
- **`src/pipelines/openpowerlifting.py`** — Web scraper (BeautifulSoup)
- **`src/dashboard/`** — Streamlit app with `Home.py` as entry point
- **`src/dashboard/config.py`** — Loads non-sensitive config from `pyproject.toml [tool.dashboard]` and secrets from `.env` or `st.secrets`
- **`src/dashboard/data.py`** — Shared data loading via DuckDB + Polars from S3 parquet (includes cached `load_daily_summary()`)
- **`src/dashboard/components.py`** — Reusable UI components (`metric_with_goal`, `date_filter_sidebar`)
- **`dbt_project/models/`** — staging (`delta_scan()`) → intermediate → marts (external parquet)

### Dashboard Pages

- **Home** — Overview with navigation cards
- **1_Recovery** — Sleep stages/totals + Meditation (bar charts with goals)
- **2_Activity** — Steps (bar chart with goal)
- **3_Nutrition_&_Body** — Macros/Calories + Weight trend + detailed tables
- **4_Exercises** — Hevy workout data + OpenPowerlifting comparisons

### Configuration Split

- **Non-sensitive** (`pyproject.toml` under `[tool.dashboard]`): S3 bucket, region, user name, goals
- **Secrets** (`.env`, not committed): AWS credentials, API keys (Hevy, Strava)

### Streamlit Quirk

Dashboard pages (`src/dashboard/pages/*.py` and `Home.py`) must call `st.set_page_config()` before other imports, so E402 (module-level import not at top) is suppressed for those files.

### DuckDB + Delta Quirk

`delta_scan()` uses DeltaKernel FFI which does NOT read DuckDB's `SET s3_*` variables. Auth must use `CREATE SECRET` (in dbt: `secrets:` block in `profiles.yml`, not `settings:`).

## Code Style

- **Python**: ruff (line-length 100, target py311, rules: E/F/I/W)
- **SQL**: sqlfluff (DuckDB dialect, jinja templater, line-length 120)
- **Commits**: conventional commits (`feat:`, `fix:`, `chore:`)
- **Pre-commit hooks**: ruff (lint + format), sqlfluff-lint, gitleaks

## Tech Stack

- **Package manager**: uv (Python 3.12.0)
- **Ingestion**: dlt with S3 filesystem destination (`table_format="delta"`)
- **Storage**: S3 (Delta tables in landing, parquet in transformed), DuckDB (in-memory OLAP)
- **Transform**: dbt-core + dbt-duckdb (profile: `health_analytics`)
- **DataFrames**: Polars
- **Dashboard**: Streamlit + Altair
- **CI**: GitHub Actions (daily at 13:00 UTC)
