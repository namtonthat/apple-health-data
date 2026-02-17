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
uv run pytest                                  # All tests
uv run pytest -k test_name                     # Single test by name
uv run pytest tests/path/to/test_file.py       # Single test file

# dbt (run from dbt_project/)
uv run dbt run --profiles-dir .
uv run dbt test --profiles-dir .
uv run dbt run --profiles-dir . --select model_name   # Single model
```

## Architecture

### Data Flow

```
Sources (APIs/files) → Landing (S3 Delta tables) → Transformed (dbt/DuckDB → S3 parquet) → Dashboard/ICS
```

### Key Modules

- **`run.py`** — CLI entry point; dispatches to pipeline stages, loads `.env` automatically. Adds `src/` to `sys.path` for pipeline imports.
- **`src/pipelines/config.py`** — Shared utilities: `get_s3_client()`, `get_duckdb_connection()` (with `CREATE SECRET` for Delta), `get_s3_destination()`, and `run_s3_pipeline()` which all pipeline runners call.
- **`src/pipelines/sources/`** — dlt source decorators: `apple_health_source()` (JSON parser), `hevy_source()` (REST API), `strava_source()` (OAuth2 REST API)
- **`src/pipelines/pipelines/`** — Thin wrappers: each calls `source() → run_s3_pipeline(name, dataset, source, date)`
- **`src/pipelines/openpowerlifting.py`** — Web scraper (BeautifulSoup)
- **`src/dashboard/data.py`** — Data loading: S3 parquet → DuckDB query → Arrow → Polars DataFrame. Central function is `load_daily_summary()` (1-hour TTL cache), used by all dashboard pages.
- **`src/dashboard/config.py`** — Loads non-sensitive config from `pyproject.toml [tool.dashboard]` and secrets from `.env` or `st.secrets`
- **`src/dashboard/components.py`** — Reusable UI components (`metric_with_goal`, `date_filter_sidebar`)

### dbt Model Layers

Three-layer architecture in `dbt_project/models/`:

- **Staging** (views) — `stg_*` models read from S3 Delta tables via `delta_scan()`, deduplicate, and rename columns
- **Intermediate** (views) — `int_*` models pivot metrics into one-row-per-day format (daily_vitals, daily_activity, daily_nutrition, daily_workouts)
- **Marts** (external parquet) — `fct_*` models materialize to S3 `transformed/` prefix. Key table: `fct_daily_summary` joins all intermediate models via full-outer date spine. Also: `fct_workout_sets`, `fct_exercise_progress`, `fct_personal_bests`, `fct_strava_activities`.

### DuckDB Auth: Two Patterns

- **Pipelines/dbt** (`src/pipelines/config.py`, `dbt_project/profiles.yml`): Use `CREATE SECRET` — required because `delta_scan()` uses DeltaKernel FFI which does NOT read DuckDB's `SET s3_*` variables.
- **Dashboard** (`src/dashboard/data.py`): Uses `SET s3_*` variables — reads parquet (not Delta), so this works fine.

### Configuration Split

- **Non-sensitive** (`pyproject.toml` under `[tool.dashboard]`): S3 bucket, region, user name, goals
- **Secrets** (`.env`, not committed): AWS credentials, API keys (Hevy, Strava)

### Streamlit Quirk

Dashboard pages (`src/dashboard/pages/*.py` and `Home.py`) must call `st.set_page_config()` before other imports, so E402 (module-level import not at top) is suppressed for those files in `pyproject.toml`.

## Code Style

- **Python**: ruff (line-length 100, target py311, rules: E/F/I/W)
- **SQL**: sqlfluff (DuckDB dialect, jinja templater, line-length 120). Excluded rules: ST06, AM04, AL01, AL09, CP02, RF04 (see `.sqlfluff` for rationale)
- **Commits**: conventional commits (`feat:`, `fix:`, `chore:`)
- **Pre-commit hooks**: ruff-check (--fix), ruff-format, sqlfluff-lint (dbt_project/models/ only), gitleaks

## Tech Stack

- **Package manager**: uv (Python 3.12.0)
- **Ingestion**: dlt with S3 filesystem destination (`table_format="delta"`)
- **Storage**: S3 (Delta tables in landing, parquet in transformed), DuckDB (in-memory OLAP)
- **Transform**: dbt-core + dbt-duckdb (profile: `health_analytics`)
- **DataFrames**: Polars
- **Dashboard**: Streamlit + Altair
- **CI**: GitHub Actions (daily at 13:00 UTC, midnight Melbourne time)
