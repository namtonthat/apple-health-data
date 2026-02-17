#!/bin/bash
set -euo pipefail

echo "========================================"
echo "Health & Fitness Data Pipeline"
echo "========================================"

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "Error: .env file not found. Copy .env.example to .env and fill in values."
    exit 1
fi

echo ""
echo "[1/4] Extracting Hevy data to landing zone..."
uv run python src/pipelines/pipelines/hevy_to_s3.py

echo ""
echo "[2/4] Extracting Apple Health data to landing zone..."
uv run python src/pipelines/pipelines/apple_health_to_s3.py

echo ""
echo "[3/4] Running dbt transformations..."
cd dbt_project
uv run dbt run

echo ""
echo "[4/4] Pipeline Complete!"
echo "========================================"
echo ""
echo "To view the dashboard:"
echo "  uv run python run.py dashboard"
