default: help

.PHONY: help
help: # Show help for each of the Makefile recipes.
	@echo ""
	@echo "  \033[1;34mSetup & Dependencies\033[0m"
	@grep -E '^(setup|test):.*#' Makefile | while read -r l; do printf "    \033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done
	@echo ""
	@echo "  \033[1;34mData Processing\033[0m"
	@grep -E '^(dbt|hevy|openpowerlifting|dags):.*#' Makefile | while read -r l; do printf "    \033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done
	@echo ""
	@echo "  \033[1;34mApplications\033[0m"
	@grep -E '^(dashboard|calendar):.*#' Makefile | while read -r l; do printf "    \033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done
	@echo ""
	@echo "  \033[1;34mInfrastructure & Deployment\033[0m"
	@grep -E '^(infra|rebuild):.*#' Makefile | while read -r l; do printf "    \033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done
	@echo ""

## Setup & Dependencies
.PHONY: setup
setup: # Install packages required for local development
	@echo "Installing packages required for local development"
	./scripts/setup.sh

.PHONY: test
test: # Run ruff / sql tests
	@echo "run ruff / sql tests"
	@./scripts/test.sh

## Data Processing
.PHONY: dbt
dbt: # Run dbt models
	@echo "running dbt models"
	@cd transforms && uv sync --group dbt && uv run dbt run && uv sync --all-groups

.PHONY: hevy
hevy: # Ingest hevy data
	@echo "running ingestion for hevy data"
	@uv sync --group ingest && uv run ingest/exercise/hevy.py && uv sync --all-groups

.PHONY: openpowerlifting
openpowerlifting: # Ingest exercise data
	@echo "running ingestion for openpowerlifting data"
	# @uv sync --group ingest && uv run ingest/exercise/openpowerlifting.py && uv sync --all-groups
	@uv run ingest/exercise/openpowerlifting.py

.PHONY: dags
dags: # Run Dagster development server
	@echo "Starting Dagster development server..."
	@./dagster/run_dagster.sh

## Applications
.PHONY: dashboard
dashboard: # Run Streamlit dashboard
	@echo "make dashboard"
	@uv run streamlit run dashboard/0_🏠_Home.py

.PHONY: calendar
calendar: # Generate calendar ICS file
	@echo "make calendar"
	./scripts/calendar.sh

## Infrastructure & Deployment
.PHONY: infra
infra: # Deploy infrastructure changes
	@echo "infra changes"
	./scripts/infra.sh

.PHONY: rebuild
rebuild: # Rebuild and deploy Lambda functions
	@echo "rebuild changes"
	./scripts/rebuild.sh
