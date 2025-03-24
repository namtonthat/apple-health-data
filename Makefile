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
	@pushd dashboard
	@streamlit run 0_🏠_Home.py

.PHONY: dbt
dbt: # run dbt models
	@echo "running dbt models"
	@pushd transforms
	@uv run dbt run
	@popd 

.PHONY: infra
infra: # deploy infra
	@echo "infra changes"
	./scripts/infra.sh

.PHONY: hevy
hevy: # ingest hevy data
	@echo "ingest hevy data"
	@echo "running ingestion for hevy data"
	@uv run ingest/exercise/hevy.py

.PHONY: rebuild
rebuild: # deploy rebuild
	@echo "rebuild changes"
	./scripts/rebuild.sh

.PHONY: setup
setup: # Install packages required for local development
	@echo "Installing packages required for local development"
	./scripts/setup.sh

