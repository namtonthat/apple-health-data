# Dagster Implementation for Apple Health Data Pipeline

This directory contains the Dagster orchestration for the Apple Health data pipeline, replacing the GitHub Actions workflow with a more robust data pipeline solution.

## Architecture

The pipeline consists of three main asset groups:

1. **Ingestion Group**: 
   - `hevy_raw_data`: Fetches workout data from Hevy API
   - `openpowerlifting_raw_data`: Fetches competition data from OpenPowerlifting

2. **Transformation Group**:
   - `dbt_transform_assets`: Runs all dbt models using the dagster-dbt integration

3. **Calendar Group**:
   - `calendar_local`: Generates ICS calendar file locally
   - `calendar_s3`: Uploads calendar to S3 bucket

## Local Development

### Prerequisites

1. Install dependencies:
   ```bash
   uv sync --group dagster
   ```

2. Set up environment variables in `.env`:
   ```bash
   AWS_REGION=your-region
   S3_BUCKET=your-bucket
   HEVY_API_KEY=your-api-key
   OPENPOWERLIFTING_USERNAME=your-username
   CALENDAR_NAME=apple-health-calendar.ics
   ```

### Running Locally

1. Start the Dagster UI:
   ```bash
   cd dagster
   uv run dagster dev
   ```

2. Open http://localhost:3000 in your browser

3. Materialize assets:
   - Click on "Assets" in the left sidebar
   - Select the assets you want to run
   - Click "Materialize selected"

### Running Jobs

The pipeline includes several job definitions:

- `apple_health_pipeline_job`: Runs the complete pipeline
- `ingestion_job`: Runs only the ingestion assets
- `transformation_job`: Runs only the dbt transformations
- `calendar_job`: Runs only the calendar generation

## Deployment

### Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t apple-health-dagster ./dagster
   ```

2. Run the container:
   ```bash
   docker run -p 3000:3000 \
     -e AWS_REGION=$AWS_REGION \
     -e S3_BUCKET=$S3_BUCKET \
     -e HEVY_API_KEY=$HEVY_API_KEY \
     -e OPENPOWERLIFTING_USERNAME=$OPENPOWERLIFTING_USERNAME \
     apple-health-dagster
   ```

### Schedule

The pipeline includes a daily schedule that runs at midnight AEST (matching the original GitHub Actions cron schedule).

## Monitoring

Dagster provides built-in monitoring capabilities:

- Asset materialization history
- Run logs and status
- Asset lineage visualization
- Failure alerts (configurable)

## Integration with Existing Infrastructure

This Dagster implementation:
- Uses the same Makefile commands as the GitHub Actions workflow
- Maintains the same S3 bucket structure
- Produces identical outputs (calendar ICS file)
- Can coexist with the existing Lambda-based infrastructure