#!/bin/bash

set -e errexit

echo "run linting checks"
uv run ruff check

echo "run sqlfluff"
uv run sqlfluff lint --dialect duckdb --templater dbt transforms/models/
