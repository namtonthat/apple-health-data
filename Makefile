default: help

.PHONY: help
help: # Show help for each of the Makefile recipes.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

.PHONY: infra
infra: # deploy infra
	@echo "infra changes"
	./scripts/infra.sh

.PHONY: calendar
calendar: # make calendar
	@echo "make calendar"
	./scripts/calendar.sh

.PHONY: setup
setup: # Install packages required for local development
	@echo "Installing packages required for local development"
	./scripts/setup.sh

