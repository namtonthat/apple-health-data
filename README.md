## Apple Health Calendar

![Apple Health Calendar](./docs/images/apple-health-calendar.jpg)

A serverless framework that automates the conversion of past daily statistics from Apple Watch into a calendar event.

```mermaid
graph LR
    A[fa:fa-mobile iPhone / Apple Watch] -->|Auto Health Export|B
    B[AWS REST API] --> C[fa:fa-aws AWS Lambda]
    C -->|ingest/labmda.py| D[saves to json]
    D -->|dbt-duckdb| E[transforms data and saves out to delta]
    E -->|create-calendar.py| F[create `ics` file <br> apple-health-calendar.ics]
```

### Detailed Process

1. A lambda function URL endpoint invokes the `ingest/lambda.py` handler function  to save the Apple Health export as is within the defined S3 bucket.
2. `dbt` alongside `duckdb` is used to transform and unnest this data to the format required for displaying information
3. `create_calendar.py` creates an `ics` calendar file with `health.parquet`. You can subscribe to this `ics` calendar to integrate with any existing Calendar service.

## Entity Relationship Diagram

```mermaid
classDiagram
    direction LR

    AppleHealthData --|> Sleep
    AppleHealthData --|> Dailys
    AppleHealthData --|> Macros

    Dailys  --|>AppleHealthEvent
    Macros --|>AppleHealthEvent
    Sleep --|>AppleHealthEvent

    class AppleHealthData { 
        date
        date_updated
        name
        qty
        source
        units
    }

    class AppleHealthEvent { 
        date
        description
        title
    }

    class Sleep { 
        sleep_analysis_asleep
        sleep_analysis_inBed
        sleep_analysis_sleepStart
    }


    class Macros { 
        carbohydrates
        protein
        total_fat
        fiber
        active_energy
    }

    class Dailys { 
        apple_exercise_time
        mindful_minutes
        step_count
        weight_body_mass
    }
```

## Project Goals

- Automate exports from iPhone (via [AutoExport](https://github.com/Lybron/health-auto-export))
- Trigger workflow automatically when AutoExport uploads into S3 endpoint.
- Create `read-only` data available in AWS S3 bucket.
- Files are refreshed in S3 bucket that personal calendar is subscribed to.

## Getting Started

This project uses `poetry` to manage environment and package dependencies

1. Setup project dependencies using `make setup`
2. Update `conf.py` to the location of the required s3 buckets
3. Run `make deploy` to deploy the terraform stack and collect the API endpoint to be used within the iOS app

![AWS API Gateway](./docs/images/api-gateway.jpg)
4. Trigger API export from `health-auto-export` using the API endpoint.

![iOS Health Auto Export - AWS Export](./docs/images/auto-export-ios.PNG)

### Advanced

You can update the emojis and definitions by looking at the `config/column.mapping.yaml` file.

### Inspiration

- Work done by [`cleverdevil/healthlake`](https://github.com/cleverdevil/healthlake).
