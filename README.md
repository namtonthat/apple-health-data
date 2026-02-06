# Health & Fitness Data Pipeline

Extract health and workout data, transform with dbt, and visualize with Streamlit.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Sources              Landing Zone           Raw Zone          Transformed  │
│  ───────              ────────────           ────────          ───────────  │
│                                                                             │
│  Hevy API      ──►    landing/hevy/     ──►  raw/hevy/    ──►  dbt models  │
│                       (parquet)              (snake_case)      (staging,    │
│                                                                marts)       │
│  Apple Health  ──►    landing/health/   ──►  raw/health/                   │
│  (JSON export)        (parquet)              (snake_case)                   │
│                                                                             │
│                                                                ▼            │
│                                                           Streamlit         │
│                                                           Dashboard         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Setup

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys and S3 bucket

# Install dependencies
uv sync
```

## Usage

### Run Full Pipeline

```bash
./scripts/run_pipeline.sh
```

### Run Individual Steps

```bash
# 1. Extract to landing zone
uv run python src/pipelines/pipelines/hevy_to_s3.py
uv run python src/pipelines/pipelines/apple_health_to_s3.py

# 2. Cleanse: landing -> raw
uv run python src/pipelines/pipelines/cleanse_to_raw.py

# 3. Transform with dbt
cd dbt_project && uv run dbt run

# 4. View dashboard
uv run streamlit run src/dashboard/app.py
```

## Data Layers

| Layer | Location | Description |
|-------|----------|-------------|
| **Landing** | `s3://{bucket}/landing/` | Raw extracted data (parquet from dlt) |
| **Raw** | `s3://{bucket}/raw/` | Cleansed data with snake_case columns and metadata |
| **Staging** | dbt views | Type casting, renaming, deduplication |
| **Intermediate** | dbt views | Business logic aggregations |
| **Marts** | dbt tables | Final analytics tables |

## Dashboard

The Streamlit dashboard shows:
- Sleep statistics and trends
- Calories burned and macros
- Exercise history with filtering
