default: help

.PHONY: help
help: # Show help for each of the Makefile recipes.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

.PHONY: calendar
calendar: # make calendar
	@echo "make calendar"
	./scripts/calendar.sh

.PHONY: dashboard
dashboard: # make dashboard
	@echo "make dashboard"
	@cd dashboard && uv run streamlit run 0_🏠_Home.py

.PHONY: dbt
dbt: # run dbt models
	@echo "running dbt models"
	@cd transforms && uv sync --group dbt && uv run dbt run && uv sync --all-groups

.PHONY: hevy
hevy: # ingest hevy data
	@echo "running ingestion for hevy data"
	@uv sync --group ingest && uv run ingest/exercise/hevy.py && uv sync --all-groups

.PHONY: openpowerlifting
openpowerlifting: # ingest exercise data
	@echo "running ingestion for openpowerlifting data"
	# @uv sync --group ingest && uv run ingest/exercise/openpowerlifting.py && uv sync --all-groups
	@uv run ingest/exercise/openpowerlifting.py

.PHONY: infra
infra: # deploy infra
	@echo "infra changes"
	./scripts/infra.sh

.PHONY: rebuild
rebuild: # deploy rebuild
	@echo "rebuild changes"
	./scripts/rebuild.sh

.PHONY: setup
setup: # Install packages required for local development
	@echo "Installing packages required for local development"
	./scripts/setup.sh

.PHONY: test
test: # run test
	@echo "run ruff / sql tests"
	@./scripts/test.sh
