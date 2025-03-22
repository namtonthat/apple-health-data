## 📱 apple-health-data

Built with
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![python](https://img.shields.io/badge/Python-3.13-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)

![Apple Health](./docs/images/apple-health-calendar.jpg)
Overview of the health data as `calendar` events

TODO: <INSERT DASHBOARD>
Dashboard view of the apple health data

### 🚀 Github Actions

[![calendar](https://github.com/namtonthat/apple-health-calendar/actions/workflows/calendar.yaml/badge.svg)](https://github.com/namtonthat/apple-health-calendar/actions/workflows/calendar.yaml)

[![test](https://github.com/namtonthat/apple-health-calendar/actions/workflows/test.yaml/badge.svg)](https://github.com/namtonthat/apple-health-calendar/actions/workflows/test.yaml)

[![infra](https://github.com/namtonthat/apple-health-calendar/actions/workflows/infra.yaml/badge.svg)](https://github.com/namtonthat/apple-health-calendar/actions/workflows/infra.yaml)

A serverless framework that automates the conversion of past daily statistics from Apple iOS into a calendar event.

```mermaid
graph LR
    A[fa:fa-mobile iPhone / Apple Watch] -->|Auto Health Export|B
    B[AWS REST API] --> C[fa:fa-aws AWS Lambda]
    C -->|ingest/lambda.py| D[saves to json]
    D -->|dbt-duckdb| E[transforms data and saves out to delta]
    E -->|calenadr/lambda.py| F[create `ics` file <br> apple-health-calendar.ics]
```

### 🎯 Project Goals

- Automate exports from iPhone (via [AutoExport](https://github.com/Lybron/health-auto-export))
- Trigger workflow automatically when AutoExport uploads into S3 endpoint.
- Create `read-only` data available in AWS S3 bucket.
- Files are refreshed in S3 bucket that personal calendar is subscribed to.
- Details about the process and entity relationship diagram are provided in the [README](https://github.com/namtonthat/apple-health-calendar/blob/main/docs/README.md)

### 🆕 Getting Started

This project uses `uv` to manage environment and package dependencies

1. Setup project dependencies using `make setup`
2. Update `conf.py` to the location of the required `s3` buckets
3. Run `make infra` to deploy the terraform stack and collect the API endpoint to be used within the iOS app
4. Trigger API export from `health-auto-export` using the API endpoint.

<p align="center">
  <img src="./docs/images/auto-export-ios.jpeg" alt="Auto Export" width="300px">
  <br>
  <em>Auto Export - iOS Version</em>
</p>

#### ⚙️ Advanced

You can update the emojis and definitions by looking at the [`calendar/event_formats.yaml`](https://github.com/namtonthat/apple-health-calendar/blob/main/calendar/events_formats.yaml) file.

#### 💡 Inspiration

- Work done by [`cleverdevil/healthlake`](https://github.com/cleverdevil/healthlake).
