#!/bin/bash

set -e

echo "Setting up Dagster development environment..."

# Go to project root
cd ..

# Install Dagster dependencies
echo "Installing Dagster dependencies..."
uv sync --group dagster

# Generate dbt manifest if it doesn't exist
echo "Generating dbt manifest..."
cd transforms
uv run dbt compile
cd ..

# Create Dagster home directory
mkdir -p dagster/.dagster

echo "✅ Dagster setup complete!"
echo ""
echo "To start Dagster, run:"
echo "  cd dagster"
echo "  uv run dagster dev"
echo ""
echo "Then open http://localhost:3000 in your browser"