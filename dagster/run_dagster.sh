#!/bin/bash
# Run Dagster development server

echo "Starting Dagster development server..."
echo "Access the UI at: http://localhost:3001"
echo ""

# Run from the dagster directory
cd "$(dirname "$0")"
uv run dagster dev -p 3001