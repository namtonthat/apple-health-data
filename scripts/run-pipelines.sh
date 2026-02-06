#!/bin/bash
# Run all data pipelines and transformations

set -e

echo "🔄 Running Data Pipelines"
echo "========================="

# Load environment
export $(cat .env | grep -v '^#' | xargs)

echo ""
echo "📥 Extracting from Hevy..."
uv run python src/pipelines/pipelines/hevy_to_s3.py

echo ""
echo "📥 Extracting from Strava..."
uv run python src/pipelines/pipelines/strava_to_s3.py || echo "⚠️  Strava skipped (credentials not configured)"

echo ""
echo "📥 Extracting from OpenPowerlifting..."
uv run python src/pipelines/openpowerlifting.py

echo ""
echo "🧹 Cleansing to raw zone..."
uv run python src/pipelines/pipelines/cleanse_to_raw.py

echo ""
echo "🔧 Running dbt transformations..."
cd dbt_project && uv run dbt run && cd ..

echo ""
echo "📅 Exporting ICS calendar..."
uv run python src/pipelines/pipelines/export_to_ics.py

echo ""
echo "========================="
echo "✅ All pipelines complete!"
