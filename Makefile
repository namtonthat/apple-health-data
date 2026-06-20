include .env
export

.PHONY: ingest transform calendar dbt-run dashboard shell all export-web web-build deploy-web

## Ingest all sources to S3 landing zone
ingest:
	uv run python run.py ingest

## Run dbt transformations (landing → transformed)
transform:
	uv run python run.py transform

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

## Regenerate the web dashboard data snapshot (web/data/dashboard.json)
export-web:
	uv run python run.py export-web

## Build the static web dashboard locally into web/out (preview the deploy build)
web-build:
	bash infra/deploy-web.sh

## Deploy the web dashboard to GitHub Pages (triggers the CI workflow)
deploy-web:
	gh workflow run deploy-web.yml --ref main
	@echo "Triggered Pages deploy. Watch: gh run watch  ·  URL: https://namtonthat.github.io/apple-health-data/"
