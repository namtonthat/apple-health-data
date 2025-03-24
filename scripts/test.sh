#!/bin/bash

set -e errexit

echo "run linting checks"
uv run ruff check

echo "run sqlfluff"
sqlfluff lint --dialect duckdb --templater jinja transforms/models/
