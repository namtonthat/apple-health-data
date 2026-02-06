# Apple Health Data Dashboard

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.54-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![dbt](https://img.shields.io/badge/dbt-1.9-FF694B?logo=dbt&logoColor=white)](https://getdbt.com)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.3-FFF000?logo=duckdb&logoColor=black)](https://duckdb.org)
[![dlt](https://img.shields.io/badge/dlt-1.21-4A154B)](https://dlthub.com)
[![AWS S3](https://img.shields.io/badge/AWS_S3-Parquet-FF9900?logo=amazons3&logoColor=white)](https://aws.amazon.com/s3/)
[![Polars](https://img.shields.io/badge/Polars-1.30-CD792C)](https://pola.rs)
[![Altair](https://img.shields.io/badge/Altair-5.5-1F77B4)](https://altair-viz.github.io)

A personal health and fitness dashboard powered by Apple Health, Hevy, and OpenPowerlifting.

## Screenshots

| Home | Recovery & Health | Exercises |
|------|-------------------|-----------|
| ![Home](docs/screenshots/home.png) | ![Recovery](docs/screenshots/recovery-health.png) | ![Exercises](docs/screenshots/exercises.png) |

## Features

- 😴 **Sleep** - Duration and stages with goal tracking
- 🍽️ **Nutrition** - Macros and calories from any app that syncs to Apple Health
- ⚖️ **Weight** - Daily trends with averages
- 🏋️ **Workouts** - Exercise logs, volume, and estimated 1RM from Hevy
- 🏆 **Powerlifting PRs** - Competition history from OpenPowerlifting
- 📅 **Calendar Export** - Subscribe to daily health summaries via ICS

## Quick Start

```bash
git clone https://github.com/namtonthat/apple-health-data.git
cd apple-health-data
./scripts/setup.sh      # Install dependencies & create .env
# Edit .env with your credentials
./scripts/run-pipelines.sh
uv run streamlit run src/dashboard/Home.py
```

## Data Sources

| Source | Data | Method |
|--------|------|--------|
| Apple Health | Sleep, Activity, Vitals | [Health Auto Export](https://www.healthyapps.dev/) to S3 |
| Nutrition App | Macros & Calories | Syncs to Apple Health |
| Hevy | Workout logs | API |
| Strava | Runs, Rides, Swims | API |
| OpenPowerlifting | Competition PRs | Web scrape |

## Calendar Subscription

The pipeline exports an ICS file you can subscribe to in any calendar app:

```
https://{bucket}.s3.{region}.amazonaws.com/exports/health_metrics.ics
```

Daily events show: `😴 7.5h sleep (1.2h deep) | 🍽️ 2000kcal (165P, 200C, 60F) | ⚖️ 75.5kg`

## Automation

GitHub Actions runs every 2 days (`.github/workflows/refresh-data.yml`).

Required secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`, `HEVY_AUTH_TOKEN`, `OPENPOWERLIFTING_URL`
