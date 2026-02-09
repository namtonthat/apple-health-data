# Apple Health Data Dashboard

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.54-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![dbt](https://img.shields.io/badge/dbt-1.11-FF694B?logo=dbt&logoColor=white)](https://getdbt.com)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.10-FFF000?logo=duckdb&logoColor=black)](https://duckdb.org)
[![dlt](https://img.shields.io/badge/dlt-1.21-4A154B)](https://dlthub.com)
[![AWS S3](https://img.shields.io/badge/AWS_S3-Parquet-FF9900?logo=amazons3&logoColor=white)](https://aws.amazon.com/s3/)
[![Polars](https://img.shields.io/badge/Polars-1.38-CD792C)](https://pola.rs)
[![Altair](https://img.shields.io/badge/Altair-6.0-1F77B4)](https://altair-viz.github.io)

A personal health and fitness dashboard powered by Apple Health, Hevy, Strava, and OpenPowerlifting.

## Screenshots

| Home | Recovery & Health | Exercises |
|------|-------------------|-----------|
| ![Home](docs/screenshots/home.png) | ![Recovery](docs/screenshots/recovery-health.png) | ![Exercises](docs/screenshots/exercises.png) |

## Features

- 😴 **Sleep** - Duration and stages with goal tracking
- 🍽️ **Nutrition** - Macros and calories from any app that syncs to Apple Health
- ⚖️ **Weight** - Daily trends with averages
- 🏋️ **Workouts** - Exercise logs, volume, and estimated 1RM from Hevy
- 🏃 **Cardio** - Runs, rides, and swims from Strava
- 🏆 **Powerlifting PRs** - Competition history from OpenPowerlifting
- 📅 **Calendar Export** - Subscribe to daily health summaries via ICS

## Quick Start

```bash
git clone https://github.com/namtonthat/apple-health-data.git
cd apple-health-data
./scripts/setup.sh                # Install dependencies & create .env
# Edit .env with your credentials
./scripts/strava-auth.sh          # Authorize Strava (optional)
uv run python run.py all          # Run full pipeline
uv run python run.py dashboard    # Start dashboard
```

## CLI Usage

All pipeline stages can be run via `run.py`, which loads `.env` automatically:

```bash
# Ingest — extract data from APIs to S3 landing zone
uv run python run.py ingest                          # All sources
uv run python run.py ingest hevy strava              # Specific sources only
uv run python run.py ingest --date 2026-01-15        # Custom extraction date

# Cleanse — landing -> raw zone
uv run python run.py cleanse                         # All sources
uv run python run.py cleanse hevy                    # Specific source only

# Transform — run dbt models
uv run python run.py transform

# Export — ICS calendar to S3
uv run python run.py export

# Full pipeline — all stages end-to-end
uv run python run.py all
uv run python run.py all --date 2026-01-15

# Dashboard — start Streamlit
uv run python run.py dashboard
```

Available ingest sources: `hevy`, `strava`, `apple-health`, `openpowerlifting`

## Configuration

Configuration is split between sensitive secrets and non-sensitive settings:

### Non-sensitive config (`pyproject.toml`)

Checked into git under `[tool.dashboard]`:

```toml
[tool.dashboard]
s3_bucket_name = "your-bucket-name"
s3_transformed_prefix = "transformed"
aws_region = "ap-southeast-2"
user_name = "Your Name"
openpowerlifting_url = "https://www.openpowerlifting.org/u/yourname"

[tool.dashboard.goals]
sleep_hours = 7.0
protein_g = 170.0
carbs_g = 300.0
fat_g = 60.0
```

### Secrets (`.env` / Streamlit Cloud)

For local development, create a `.env` file:

```bash
# Required
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Optional (for additional features)
HEVY_API_KEY=your-hevy-key
STRAVA_CLIENT_ID=your-client-id
STRAVA_CLIENT_SECRET=your-client-secret
STRAVA_REFRESH_TOKEN=your-refresh-token
```

For Streamlit Cloud deployment, generate and copy secrets:

```bash
python scripts/generate_streamlit_secrets.py
# Then copy .streamlit/secrets.toml contents to Streamlit Cloud settings
```

## Data Sources

| Source | Data | Method |
|--------|------|--------|
| Apple Health | Sleep, Activity, Vitals | [Health Auto Export](https://www.healthyapps.dev/) to S3 |
| Nutrition App | Macros & Calories | Syncs to Apple Health |
| Hevy | Workout logs | API |
| Strava | Runs, Rides, Swims | API ([create app](https://www.strava.com/settings/api)) |
| OpenPowerlifting | Competition PRs | Web scrape |

## Calendar Subscription

The pipeline exports an ICS file you can subscribe to in any calendar app:

```
https://{bucket}.s3.{region}.amazonaws.com/exports/health_metrics.ics
```

Daily events show:

```
😴 7.5h sleep (1.2h deep, 1.8h REM)
🍽️ 2000kcal (165P, 200C, 60F)
⚖️ 75.5kg · 🚶 8,432 steps
```

## Deployment

### Streamlit Cloud

Deploy the dashboard to Streamlit Cloud:

1. Fork/push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo
3. Set the main file path to `src/dashboard/Home.py`
4. Add secrets (Settings → Secrets) - generate with `python scripts/generate_streamlit_secrets.py`

See [Streamlit Cloud documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app) for detailed instructions.

### CI/CD

GitHub Actions automatically refreshes data daily via `.github/workflows/refresh-data.yml`.

#### Required GitHub Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `AWS_ACCESS_KEY_ID` | Yes | AWS credentials for S3 access |
| `AWS_SECRET_ACCESS_KEY` | Yes | AWS credentials for S3 access |
| `HEVY_API_KEY` | No | For workout data from Hevy |
| `STRAVA_CLIENT_ID` | No | For Strava activities |
| `STRAVA_CLIENT_SECRET` | No | For Strava activities |
| `STRAVA_REFRESH_TOKEN` | No | For Strava activities |

Non-sensitive values (bucket name, goals, URLs) are read from `pyproject.toml`.

#### Manual Trigger

You can manually trigger a data refresh from the Actions tab in GitHub.

## Project Structure

```
apple-health-data/
├── run.py                  # CLI runner (see CLI Usage)
├── src/
│   ├── dashboard/          # Streamlit app
│   │   ├── Home.py
│   │   └── pages/
│   └── pipelines/          # Data pipelines (dlt)
├── dbt_project/            # dbt transformations
├── scripts/                # Setup and utility scripts
├── .github/workflows/      # CI/CD
├── pyproject.toml          # Dependencies + dashboard config
└── .env                    # Secrets (not committed)
```
