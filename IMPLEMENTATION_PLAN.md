# Hevy API Data Pipeline Implementation Plan

## Overview
Extract workout data from Hevy API using `dlt`, land raw data in S3 under `raw/` prefix with minimal transformation (only metadata), then use `dbt` to normalize into daily exercise rows.

**Design Principles:**
- Land data as close to source as possible
- Only add dlt metadata columns (`_dlt_load_id`, `_dlt_id`, `_dlt_extracted_at`)
- Use dlt's native capabilities (no custom transformations in extraction)
- dbt handles all business logic transformations

---

## 1. Project Setup with uv

### Initialize Project
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Initialize project
uv init hevy-pipeline
cd hevy-pipeline

# Add dependencies
uv add dlt[filesystem,s3] dbt-core dbt-duckdb python-dotenv
```

### Project Structure
```
hevy-pipeline/
├── pyproject.toml
├── .env                          # API keys and AWS credentials
├── .env.example                  # Template for .env
├── .gitignore
├── src/
│   └── hevy_pipeline/
│       ├── __init__.py
│       ├── sources/
│       │   └── hevy.py           # dlt source for Hevy API
│       └── pipelines/
│           └── hevy_to_s3.py     # Pipeline runner
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── sources.yml           # dbt source definitions
│   │   ├── staging/
│   │   │   ├── _stg__models.yml
│   │   │   ├── stg_hevy__workouts.sql
│   │   │   ├── stg_hevy__exercises.sql
│   │   │   └── stg_hevy__sets.sql
│   │   └── marts/
│   │       └── daily_exercises.sql
│   └── tests/
└── scripts/
    └── run_pipeline.sh
```

---

## 2. Environment Configuration

### Option A: Project `.env` File (Recommended for this project)

All credentials stay within the project directory.

#### .env.example (commit this)
```env
# ===================
# Hevy API
# ===================
HEVY_API_KEY=

# ===================
# AWS Credentials
# ===================
# Create an IAM user with the policy below, then generate access keys
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=ap-southeast-2

# ===================
# S3 Configuration
# ===================
S3_BUCKET_NAME=
S3_RAW_PREFIX=raw
S3_TRANSFORMED_PREFIX=transformed

# ===================
# Pipeline Settings
# ===================
DLT_PIPELINE_DIR=.dlt_pipelines
```

#### .env (DO NOT commit - copy from .env.example)
```bash
cp .env.example .env
# Then fill in your actual values
```

---

### Option B: AWS CLI Configuration (System-wide)

If you prefer using AWS CLI profiles, configure these files:

#### ~/.aws/credentials
```ini
[hevy-pipeline]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
```

#### ~/.aws/config
```ini
[profile hevy-pipeline]
region = ap-southeast-2
output = json
```

Then update `.env` to use the profile:
```env
# Use AWS profile instead of explicit credentials
AWS_PROFILE=hevy-pipeline
AWS_DEFAULT_REGION=ap-southeast-2

# S3 Configuration
S3_BUCKET_NAME=your-bucket-name
S3_RAW_PREFIX=raw
S3_TRANSFORMED_PREFIX=transformed
```

And update the pipeline code to use profile:
```python
# In hevy_to_s3.py, credentials become:
credentials={
    "profile_name": os.environ.get("AWS_PROFILE", "hevy-pipeline"),
}
```

---

### AWS IAM Policy (Minimum Permissions)

Create an IAM user/role with this policy. Replace `YOUR_BUCKET_NAME` with your actual bucket.

#### iam-policy-hevy-pipeline.json
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "S3BucketAccess",
            "Effect": "Allow",
            "Action": [
                "s3:GetBucketLocation",
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME"
        },
        {
            "Sid": "S3ObjectAccess",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
        }
    ]
}
```

#### Create via AWS CLI
```bash
# Create the policy
aws iam create-policy \
    --policy-name hevy-pipeline-s3-access \
    --policy-document file://iam-policy-hevy-pipeline.json

# Create IAM user
aws iam create-user --user-name hevy-pipeline-user

# Attach policy to user
aws iam attach-user-policy \
    --user-name hevy-pipeline-user \
    --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/hevy-pipeline-s3-access

# Generate access keys
aws iam create-access-key --user-name hevy-pipeline-user
# Save the AccessKeyId and SecretAccessKey from output
```

---

### S3 Bucket Setup

```bash
# Create bucket (if it doesn't exist)
aws s3 mb s3://YOUR_BUCKET_NAME --region ap-southeast-2

# Verify access
aws s3 ls s3://YOUR_BUCKET_NAME/
```

---

### .gitignore
```gitignore
# Secrets
.env
*.pem
*.key

# dlt
.dlt_pipelines/
.dlt/

# Python
__pycache__/
*.pyc
.venv/
venv/

# dbt
dbt_project/target/
dbt_project/logs/
dbt_project/dbt_packages/

# DuckDB
*.duckdb
*.duckdb.wal

# IDE
.idea/
.vscode/
*.swp
```

---

## 3. dlt Source - Raw Data Extraction

### src/hevy_pipeline/sources/hevy.py

```python
"""
dlt source for Hevy API.

Extracts data as close to source as possible.
Only dlt metadata is added (_dlt_load_id, _dlt_id, _dlt_parent_id).

API Documentation: https://api.hevyapp.com/docs/

Confirmed API details:
- Base URL: https://api.hevyapp.com/v1
- Auth: api-key header
- Pagination: page & pageSize query params
"""
import dlt
from dlt.sources.helpers.rest_client import RESTClient
from dlt.sources.helpers.rest_client.paginators import PageNumberPaginator
import os
from typing import Iterator


# ===================
# Configuration (confirmed from API docs)
# ===================
BASE_URL = "https://api.hevyapp.com/v1"


def _get_client() -> RESTClient:
    """Create REST client with authentication."""
    api_key = os.environ.get("HEVY_API_KEY")
    if not api_key:
        raise ValueError("HEVY_API_KEY environment variable required")

    return RESTClient(
        base_url=BASE_URL,
        headers={
            "api-key": api_key,
            "accept": "application/json",
        },
        paginator=PageNumberPaginator(
            page_param="page",
            page_size=100,
            page_size_param="pageSize",
            total_path="page_count",  # Response includes total pages
            base_page=1,
        ),
    )


@dlt.source(name="hevy", max_table_nesting=2)
def hevy_source(
    workouts: bool = True,
    exercise_templates: bool = True,
    routines: bool = True,
):
    """
    Hevy API source.

    Args:
        workouts: Extract workouts with exercises and sets
        exercise_templates: Extract exercise template definitions
        routines: Extract saved routines

    Yields data as-is from API, dlt adds:
        - _dlt_load_id: Unique load identifier
        - _dlt_id: Unique row identifier
        - Automatic nested table extraction (workouts__exercises, workouts__exercises__sets)
    """
    resources = []

    if workouts:
        resources.append(workouts_resource())
    if exercise_templates:
        resources.append(exercise_templates_resource())
    if routines:
        resources.append(routines_resource())

    return resources


@dlt.resource(
    name="workouts",
    write_disposition="merge",
    primary_key="id",
    columns={"id": {"nullable": False}},
)
def workouts_resource() -> Iterator[dict]:
    """
    Extract workouts with nested exercises and sets.

    dlt will automatically:
    - Flatten nested 'exercises' into 'workouts__exercises' table
    - Flatten nested 'sets' into 'workouts__exercises__sets' table
    - Add _dlt_parent_id for relationships

    Response structure:
    {
        "page": 1,
        "page_count": 5,
        "workouts": [
            {
                "id": "uuid",
                "title": "Morning Workout 💪",
                "routine_id": "uuid",
                "description": "...",
                "start_time": "2021-09-14T12:00:00Z",
                "end_time": "2021-09-14T12:00:00Z",
                "created_at": "2021-09-14T12:00:00Z",
                "updated_at": "2021-09-14T12:00:00Z",
                "exercises": [
                    {
                        "index": 0,
                        "title": "Bench Press (Barbell)",
                        "exercise_template_id": "05293BCA",
                        "supersets_id": 0,
                        "notes": "...",
                        "sets": [
                            {
                                "index": 0,
                                "type": "normal",
                                "weight_kg": 100,
                                "reps": 10,
                                "distance_meters": null,
                                "duration_seconds": null,
                                "rpe": 9.5,
                                "custom_metric": 50
                            }
                        ]
                    }
                ]
            }
        ]
    }
    """
    client = _get_client()

    for page in client.paginate("workouts"):
        response = page.json() if hasattr(page, 'json') else page
        yield from response.get("workouts", [])


@dlt.resource(
    name="exercise_templates",
    write_disposition="replace",
    primary_key="id",
)
def exercise_templates_resource() -> Iterator[dict]:
    """
    Extract exercise template definitions.
    These are the master list of exercises available in Hevy.
    """
    client = _get_client()

    for page in client.paginate("exercise_templates"):
        response = page.json() if hasattr(page, 'json') else page
        yield from response.get("exercise_templates", [])


@dlt.resource(
    name="routines",
    write_disposition="replace",
    primary_key="id",
)
def routines_resource() -> Iterator[dict]:
    """
    Extract saved workout routines/templates.
    """
    client = _get_client()

    for page in client.paginate("routines"):
        response = page.json() if hasattr(page, 'json') else page
        yield from response.get("routines", [])
```

---

## 4. Pipeline Runner

### src/hevy_pipeline/pipelines/hevy_to_s3.py

```python
"""
Pipeline: Hevy API -> S3 (raw/)

Loads data to S3 filesystem destination with minimal transformation.
Data lands as Parquet files under the raw/ prefix.
"""
import dlt
from dlt.destinations import filesystem
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from sources.hevy import hevy_source

load_dotenv()


def get_s3_destination():
    """Configure S3 filesystem destination."""
    bucket = os.environ["S3_BUCKET_NAME"]
    prefix = os.environ.get("S3_RAW_PREFIX", "raw")

    return filesystem(
        bucket_url=f"s3://{bucket}/{prefix}",
        credentials={
            "aws_access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
            "aws_secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
            "region_name": os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-2"),
        },
    )


def run_pipeline():
    """
    Run the Hevy to S3 extraction pipeline.

    Data lands in: s3://{bucket}/raw/hevy/
    """
    pipeline = dlt.pipeline(
        pipeline_name="hevy_to_s3",
        destination=get_s3_destination(),
        dataset_name="hevy",
        pipelines_dir=os.environ.get("DLT_PIPELINE_DIR", ".dlt_pipelines"),
    )

    # Extract all resources - data lands as-is with dlt metadata only
    source = hevy_source(
        workouts=True,
        exercise_templates=True,
        routines=True,
    )

    # Run extraction
    load_info = pipeline.run(
        source,
        loader_file_format="parquet",  # Land as Parquet for efficient querying
    )

    print("=" * 60)
    print("Pipeline Complete")
    print("=" * 60)
    print(f"Load info: {load_info}")
    print(f"\nDestination: s3://{os.environ['S3_BUCKET_NAME']}/{os.environ.get('S3_RAW_PREFIX', 'raw')}/hevy/")

    # Show what tables were created
    print("\nTables loaded:")
    for table in load_info.load_packages[0].schema.tables:
        if not table.startswith("_dlt"):
            print(f"  - {table}")

    return load_info


if __name__ == "__main__":
    run_pipeline()
```

---

## 5. S3 Raw Data Structure

After pipeline runs, data lands in S3:

```
s3://{bucket}/
└── raw/
    └── hevy/
        ├── _dlt_loads/                           # dlt internal tracking
        │   └── *.parquet
        ├── _dlt_pipeline_state/                  # Pipeline state for incremental
        │   └── *.parquet
        ├── workouts/                             # Raw workout records
        │   └── *.parquet
        ├── workouts__exercises/                  # Flattened exercises (auto by dlt)
        │   └── *.parquet
        ├── workouts__exercises__sets/            # Flattened sets (auto by dlt)
        │   └── *.parquet
        ├── exercise_templates/                   # Exercise definitions
        │   └── *.parquet
        └── routines/                             # Saved routines
            └── *.parquet
```

### Raw Data Columns (added by dlt)

Each table includes these dlt metadata columns:
- `_dlt_load_id` - Identifies the load batch
- `_dlt_id` - Unique row identifier
- `_dlt_parent_id` - FK to parent table (nested tables only)
- `_dlt_list_idx` - Index in parent array (nested tables only)

**All source fields preserved exactly as returned from API.**

---

## 6. dbt Transformation Layer

### dbt_project/dbt_project.yml

```yaml
name: 'hevy_transforms'
version: '1.0.0'
config-version: 2

profile: 'hevy_transforms'

model-paths: ["models"]
seed-paths: ["seeds"]
test-paths: ["tests"]
macro-paths: ["macros"]

vars:
  s3_bucket: "{{ env_var('S3_BUCKET_NAME') }}"
  s3_raw_prefix: "{{ env_var('S3_RAW_PREFIX', 'raw') }}"

models:
  hevy_transforms:
    staging:
      +materialized: view
      +schema: staging
    marts:
      +materialized: table
      +schema: marts
```

### dbt_project/profiles.yml

```yaml
hevy_transforms:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "{{ env_var('DBT_DUCKDB_PATH', 'hevy.duckdb') }}"
      extensions:
        - httpfs
        - parquet
      settings:
        s3_region: "{{ env_var('AWS_DEFAULT_REGION', 'ap-southeast-2') }}"
        s3_access_key_id: "{{ env_var('AWS_ACCESS_KEY_ID') }}"
        s3_secret_access_key: "{{ env_var('AWS_SECRET_ACCESS_KEY') }}"
```

### dbt_project/models/sources.yml

```yaml
version: 2

sources:
  - name: hevy_raw
    description: "Raw data from Hevy API loaded via dlt"
    meta:
      loader: dlt
      loaded_at_field: _dlt_load_id

    tables:
      - name: workouts
        description: "Raw workout sessions"
        meta:
          external_location: "s3://{{ var('s3_bucket') }}/{{ var('s3_raw_prefix') }}/hevy/workouts/*.parquet"

      - name: workouts__exercises
        description: "Exercises within workouts (flattened by dlt)"
        meta:
          external_location: "s3://{{ var('s3_bucket') }}/{{ var('s3_raw_prefix') }}/hevy/workouts__exercises/*.parquet"

      - name: workouts__exercises__sets
        description: "Sets within exercises (flattened by dlt)"
        meta:
          external_location: "s3://{{ var('s3_bucket') }}/{{ var('s3_raw_prefix') }}/hevy/workouts__exercises__sets/*.parquet"

      - name: exercise_templates
        description: "Exercise definitions/templates"
        meta:
          external_location: "s3://{{ var('s3_bucket') }}/{{ var('s3_raw_prefix') }}/hevy/exercise_templates/*.parquet"
```

### dbt_project/models/staging/stg_hevy__workouts.sql

```sql
-- Staging layer: minimal transformation, type casting, renaming
{{ config(materialized='view') }}

select
    -- Primary key
    id as workout_id,

    -- Foreign keys
    routine_id,

    -- Attributes
    title as workout_title,
    description as workout_description,

    -- Timestamps
    start_time::timestamp as started_at,
    end_time::timestamp as ended_at,
    date(start_time::timestamp) as workout_date,
    created_at::timestamp as created_at,
    updated_at::timestamp as updated_at,

    -- dlt metadata
    _dlt_load_id,
    _dlt_id

from read_parquet('s3://{{ var("s3_bucket") }}/{{ var("s3_raw_prefix") }}/hevy/workouts/*.parquet')
```

### dbt_project/models/staging/stg_hevy__exercises.sql

```sql
{{ config(materialized='view') }}

select
    -- Keys
    _dlt_id as exercise_id,
    _dlt_parent_id as workout_id,

    -- Attributes
    title as exercise_title,
    exercise_template_id,
    index as exercise_index,
    supersets_id,
    notes as exercise_notes,

    -- dlt metadata
    _dlt_load_id,
    _dlt_list_idx

from read_parquet('s3://{{ var("s3_bucket") }}/{{ var("s3_raw_prefix") }}/hevy/workouts__exercises/*.parquet')
```

### dbt_project/models/staging/stg_hevy__sets.sql

```sql
{{ config(materialized='view') }}

select
    -- Keys
    _dlt_id as set_id,
    _dlt_parent_id as exercise_id,

    -- Attributes
    index as set_index,
    type as set_type,
    weight_kg,
    reps,
    distance_meters,
    duration_seconds,
    rpe,
    custom_metric,

    -- dlt metadata
    _dlt_load_id,
    _dlt_list_idx

from read_parquet('s3://{{ var("s3_bucket") }}/{{ var("s3_raw_prefix") }}/hevy/workouts__exercises__sets/*.parquet')
```

### dbt_project/models/staging/stg_hevy__exercise_templates.sql

```sql
{{ config(materialized='view') }}

select
    -- Primary key
    id as exercise_template_id,

    -- Attributes
    title as exercise_name,
    type as exercise_type,
    primary_muscle_group,
    secondary_muscle_groups,
    is_custom,

    -- dlt metadata
    _dlt_load_id,
    _dlt_id

from read_parquet('s3://{{ var("s3_bucket") }}/{{ var("s3_raw_prefix") }}/hevy/exercise_templates/*.parquet')
```

### dbt_project/models/marts/daily_exercises.sql

```sql
-- Final output: One row per set per day
-- Columns: date, exercise_name, kg, reps (plus supporting fields)
{{ config(materialized='table') }}

with workouts as (
    select * from {{ ref('stg_hevy__workouts') }}
),

exercises as (
    select * from {{ ref('stg_hevy__exercises') }}
),

sets as (
    select * from {{ ref('stg_hevy__sets') }}
),

joined as (
    select
        -- Date
        w.workout_date,

        -- Exercise identification (use title from exercise, which comes from API)
        e.exercise_title as exercise_name,

        -- Set data
        s.set_index + 1 as set_number,
        s.weight_kg,
        s.reps,
        s.set_type,
        s.rpe,

        -- Additional context
        w.workout_title,
        w.started_at,
        w.ended_at,

        -- IDs for traceability
        w.workout_id,
        e.exercise_id,
        s.set_id,
        e.exercise_template_id

    from sets s
    inner join exercises e on s.exercise_id = e.exercise_id
    inner join workouts w on e.workout_id = w.workout_id
)

select
    workout_date,
    exercise_name,
    weight_kg,
    reps,
    set_number,
    set_type,
    rpe,
    workout_title,
    started_at,
    ended_at,
    workout_id,
    exercise_id,
    set_id

from joined
where weight_kg is not null
   or reps is not null

order by
    workout_date desc,
    started_at desc,
    exercise_name,
    set_number
```

---

## 7. Running Everything

### scripts/run_pipeline.sh

```bash
#!/bin/bash
set -euo pipefail

echo "================================"
echo "Hevy Data Pipeline"
echo "================================"

# Load environment
source .env

echo ""
echo "[1/3] Extracting from Hevy API to S3..."
uv run python src/hevy_pipeline/pipelines/hevy_to_s3.py

echo ""
echo "[2/3] Running dbt transformations..."
cd dbt_project
uv run dbt deps
uv run dbt run

echo ""
echo "[3/3] Validating output..."
uv run dbt test

echo ""
echo "================================"
echo "Pipeline Complete!"
echo "================================"
echo ""
echo "Query results with:"
echo "  uv run dbt show --select daily_exercises --limit 20"
```

### CLI Commands

```bash
# Make executable
chmod +x scripts/run_pipeline.sh

# Run full pipeline
./scripts/run_pipeline.sh

# Or run steps individually:

# 1. Extract to S3
uv run python src/hevy_pipeline/pipelines/hevy_to_s3.py

# 2. Transform with dbt
cd dbt_project
uv run dbt run

# 3. Query results
uv run dbt show --select daily_exercises --limit 20
```

---

## 8. Output Schema

The final `daily_exercises` table:

| Column | Type | Description |
|--------|------|-------------|
| `workout_date` | DATE | Date of workout |
| `exercise_name` | VARCHAR | Exercise name (e.g., "Bench Press (Barbell)") |
| `weight_kg` | FLOAT | Weight in kilograms |
| `reps` | INT | Number of repetitions |
| `set_number` | INT | Set number (1, 2, 3...) |
| `set_type` | VARCHAR | Type: normal, warmup, dropset, failure |
| `rpe` | FLOAT | Rate of perceived exertion (1-10) |
| `workout_title` | VARCHAR | Workout session name |
| `started_at` | TIMESTAMP | Workout start time |
| `ended_at` | TIMESTAMP | Workout end time |
| `workout_id` | VARCHAR | FK to workout |
| `exercise_id` | VARCHAR | FK to exercise |
| `set_id` | VARCHAR | Unique set ID |

### Example Output

| workout_date | exercise_name | weight_kg | reps | set_number | set_type |
|--------------|---------------|-----------|------|------------|----------|
| 2025-02-05 | Bench Press (Barbell) | 100.0 | 10 | 1 | normal |
| 2025-02-05 | Bench Press (Barbell) | 100.0 | 8 | 2 | normal |
| 2025-02-05 | Bench Press (Barbell) | 100.0 | 6 | 3 | normal |
| 2025-02-05 | Squat (Barbell) | 120.0 | 8 | 1 | normal |
| 2025-02-05 | Squat (Barbell) | 130.0 | 6 | 2 | normal |

---

## 9. API Configuration (Confirmed)

```bash
# Example API call
curl -X 'GET' \
  'https://api.hevyapp.com/v1/workouts?page=1&pageSize=5' \
  -H 'accept: application/json' \
  -H 'api-key: YOUR_API_KEY'
```

### Confirmed Details

| Setting | Value |
|---------|-------|
| Base URL | `https://api.hevyapp.com/v1` |
| Auth Header | `api-key: {key}` |
| Pagination | `page` & `pageSize` query params |
| Response wrapper | `{"page": 1, "page_count": 5, "workouts": [...]}` |

### Confirmed Response Schema

```json
{
  "page": 1,
  "page_count": 5,
  "workouts": [
    {
      "id": "uuid",
      "title": "Morning Workout 💪",
      "routine_id": "uuid",
      "description": "...",
      "start_time": "2021-09-14T12:00:00Z",
      "end_time": "2021-09-14T12:00:00Z",
      "updated_at": "2021-09-14T12:00:00Z",
      "created_at": "2021-09-14T12:00:00Z",
      "exercises": [
        {
          "index": 0,
          "title": "Bench Press (Barbell)",
          "notes": "...",
          "exercise_template_id": "05293BCA",
          "supersets_id": 0,
          "sets": [
            {
              "index": 0,
              "type": "normal",
              "weight_kg": 100,
              "reps": 10,
              "distance_meters": null,
              "duration_seconds": null,
              "rpe": 9.5,
              "custom_metric": 50
            }
          ]
        }
      ]
    }
  ]
}
```

---

## Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| Package Manager | uv | Python dependency management |
| Extract | dlt | API extraction with auto-flattening |
| Raw Storage | S3 (raw/) | Parquet files, source-faithful + dlt metadata |
| Transform | dbt + DuckDB | SQL transformations, S3 direct query |
| Output | daily_exercises | Normalized rows: date, exercise, kg, reps |
