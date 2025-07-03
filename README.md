## 📱 apple-health-data

Built with [![python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://www.python.org)

#### 🚀 Github Actions

[![calendar](https://github.com/namtonthat/apple-health-data/actions/workflows/calendar.yaml/badge.svg)](https://github.com/namtonthat/apple-health-data/actions/workflows/calendar.yaml)
[![test](https://github.com/namtonthat/apple-health-data/actions/workflows/test.yaml/badge.svg)](https://github.com/namtonthat/apple-health-data/actions/workflows/test.yaml)
[![infra](https://github.com/namtonthat/apple-health-data/actions/workflows/infra.yaml/badge.svg)](https://github.com/namtonthat/apple-health-data/actions/workflows/infra.yaml)

## Purpose

A serverless data pipeline that processes Apple Health data into calendar events and dashboards, orchestrated by Dagster.

```mermaid
graph LR
    A[fa:fa-mobile iPhone / Apple Watch] -->|Auto Health Export| B[AWS REST API]
    B --> C[fa:fa-aws Lambda: Ingest]
    C -->|JSON| D[fa:fa-database S3 Raw Data]
    
    subgraph Dagster Pipeline
        D --> E[fa:fa-cogs Ingestion Assets<br/>Hevy & OpenPowerlifting]
        E --> F[fa:fa-transform dbt Assets<br/>Staging → Raw → Semantic]
        F --> G[fa:fa-calendar Calendar Asset<br/>Generate ICS]
    end
    
    G --> H[fa:fa-file S3: Calendar ICS]
    F --> I[fa:fa-chart-line Streamlit Dashboard]
```

## 🎯 Project Goals

- Automate exports from iPhone (via [AutoExport](https://github.com/Lybron/health-auto-export))
- Trigger workflow automatically when AutoExport uploads into S3 endpoint.
- Create `read-only` data available in AWS S3 bucket.
- Files are refreshed in S3 bucket that personal calendar is subscribed to.
- Details about the process and entity relationship diagram are provided in the [README](https://github.com/namtonthat/apple-health-calendar/blob/main/docs/README.md)

> [!important]
> With the `sleep` data, it ignores intra sleep stats

## Screenshots

### 📅 Calendar

![Apple Health](./docs/images/apple-health-calendar.jpg)
Overview of the health data as `calendar` events

### 📄 Dashboard

A dashboard was also created with `streamlit` and hosted on [`namtonthat.streamlit.app`](https://namtonthat.streamlit.app)

![Dashboard](./docs/images/apple-dashboard.png)

### 🆕 Getting Started

This project uses `uv` to manage environment and package dependencies

1. Setup project dependencies using `make setup`
2. Create a `.env` (based off the [`.env.example`](.env.example)) to define the specific infra requirements
3. Run `make infra` to deploy the terraform stack and collect the API endpoint to be used within the iOS app
4. Trigger API export from `health-auto-export` using the API endpoint
5. Deploy Dagster for orchestration:
   ```bash
   cd dagster && ./setup.sh
   docker-compose up -d
   ```
6. Access Dagster UI at http://localhost:3000 to monitor pipeline runs

<p align="center">
  <img src="./docs/images/auto-export-ios.jpeg" alt="Auto Export" width="300px">
  <br>
  <em>Auto Export - iOS Version</em>
</p>

#### ⚙️ Advanced

You can update the emojis and definitions by looking at the [`calendar/event_formats.yaml`](https://github.com/namtonthat/apple-health-calendar/blob/main/calendar/events_formats.yaml) file.

#### 💡 Inspiration

- Work done by [`cleverdevil/healthlake`](https://github.com/cleverdevil/healthlake).
