include .env
export

.PHONY: ingest transform calendar dbt-run dashboard shell all

## Ingest all sources to S3 landing zone
ingest:
	uv run python run.py ingest

## Run dbt transformations (landing → transformed)
transform:
	uv run python run.py transform

## Alias for transform
dbt-run: transform

## Export ICS calendar to S3
calendar:
	uv run python run.py export

## Start Streamlit dashboard
dashboard:
	uv run python run.py dashboard

## Open DuckDB shell connected to S3 transformed tables
shell:
	uv run python scripts/duckdb_shell.py

## Run full pipeline (ingest → transform → calendar)
all:
	uv run python run.py all
