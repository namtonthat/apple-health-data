#!/bin/bash
# Setup script for Apple Health Data Dashboard

set -e

echo "🏥 Apple Health Data Dashboard - Setup"
echo "======================================="

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Install it from: https://github.com/astral-sh/uv"
    exit 1
fi
echo "✅ uv found"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
uv sync

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=ap-southeast-2
S3_BUCKET_NAME=your_bucket_name

# Hevy API (get from Hevy app settings)
HEVY_API_KEY=your_hevy_api_key

# Strava API (create app at https://www.strava.com/settings/api)
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REFRESH_TOKEN=your_refresh_token

# OpenPowerlifting Profile URL
OPENPOWERLIFTING_URL=https://www.openpowerlifting.org/u/yourname

# User Display Name
USER_NAME="Your Name"

# Health Goals
GOAL_SLEEP_HOURS=7.0
GOAL_PROTEIN_G=170.0
GOAL_CARBS_G=300.0
GOAL_FAT_G=60.0
EOF
    echo "✅ .env created - edit it with your credentials"
else
    echo "✅ .env already exists"
fi

echo ""
echo "======================================="
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your credentials"
echo "  2. Run pipelines:  uv run python run.py all"
echo "  3. Run dashboard:  uv run streamlit run src/dashboard/Home.py"
echo ""
