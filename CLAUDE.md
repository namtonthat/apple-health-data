# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Setup and Dependencies
- `make setup` - Install packages required for local development (uses uv package manager)
- `uv sync` - Sync all dependencies from pyproject.toml
- `uv sync --group <group>` - Sync specific dependency group (dashboard, dbt, ingest, test)

### Testing and Linting
- `make test` - Run all tests and linting checks (ruff, sqlfluff, pytest)
- `uv run ruff check` - Run Python linter
- `uv run sqlfluff lint --dialect duckdb --templater dbt transforms/models/` - Lint SQL files
- `uv run pytest` - Run Python tests
- `uv run pytest tests/test_helpers.py::test_specific_function` - Run a single test

### Data Processing
- `make dbt` - Run dbt models to transform health data
- `make hevy` - Ingest Hevy workout data
- `make openpowerlifting` - Ingest OpenPowerlifting competition data

### Infrastructure and Deployment
- `make infra` - Deploy infrastructure changes via Terraform
- `make rebuild` - Rebuild and deploy Lambda functions

### Application Features
- `make dashboard` - Run Streamlit dashboard locally (http://localhost:8501)
- `make calendar` - Generate calendar ICS file from health data

## Architecture Overview

This is a serverless data pipeline that processes Apple Health data into calendar events and dashboards.

### Data Flow
1. **Ingestion**: iPhone/Apple Watch → Auto Health Export app → AWS API Gateway → Lambda (`ingest/lambda.py`) → S3 (JSON)
2. **Transformation**: S3 → dbt-duckdb → Parquet files in S3
3. **Presentation**: 
   - Calendar: Lambda (`calendar/lambda.py`) → ICS file
   - Dashboard: Streamlit app reading from DuckDB/Parquet

### Key Components

#### Data Layers (dbt models)
- **Staging** (`transforms/models/staging/`): Reads raw data from S3, applies timezone conversion
- **Raw** (`transforms/models/raw/`): Unnests JSON structures, deduplicates data
- **Semantic** (`transforms/models/semantic/`): Business logic, metric calculations, aggregations

#### Lambda Functions
- `ingest/lambda.py`: Receives health data from iOS app, saves to S3
- `transforms/lambda.py`: Triggers dbt transformations
- `calendar/lambda.py`: Generates ICS calendar file from processed data

#### Dashboard (`dashboard/`)
- Streamlit-based web app with pages for Home, Exercises, Mental Health, and Nutrition
- Uses Altair for visualizations
- Reads data directly from DuckDB/Parquet files

### Infrastructure
- **AWS Services**: Lambda, S3, API Gateway, ECR
- **IaC**: Terraform modules in `infra/`
- **CI/CD**: GitHub Actions workflows for testing, infrastructure updates, and calendar generation

### Data Sources
- Apple Health metrics (via Auto Health Export app)
- Hevy workout tracking app
- OpenPowerlifting competition data

### Important Patterns
- All timestamps converted to Melbourne timezone
- Incremental loading with 14-15 day lookback windows
- Metric deduplication using window functions
- Calendar events configured via `calendar/event_formats.yaml`