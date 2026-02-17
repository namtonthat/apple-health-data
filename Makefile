include .env
export

DBT_DIR := dbt_project
DBT := uv run dbt
DBT_FLAGS := --profiles-dir . --project-dir .

.PHONY: dbt-run dbt-test dbt-build dbt-clean dbt-debug dbt-docs dbt-deps dbt-run-model dbt-lint

## Run all dbt models
dbt-run:
	cd $(DBT_DIR) && $(DBT) run $(DBT_FLAGS)

## Run dbt tests
dbt-test:
	cd $(DBT_DIR) && $(DBT) test $(DBT_FLAGS)

## Run + test (build)
dbt-build:
	cd $(DBT_DIR) && $(DBT) build $(DBT_FLAGS)

## Run a single model: make dbt-run-model MODEL=fct_daily_summary
dbt-run-model:
	cd $(DBT_DIR) && $(DBT) run $(DBT_FLAGS) --select $(MODEL)

## Clean dbt artifacts
dbt-clean:
	cd $(DBT_DIR) && $(DBT) clean $(DBT_FLAGS)

## Verify dbt connection
dbt-debug:
	cd $(DBT_DIR) && $(DBT) debug $(DBT_FLAGS)

## Install dbt packages
dbt-deps:
	cd $(DBT_DIR) && $(DBT) deps $(DBT_FLAGS)

## Generate dbt docs
dbt-docs:
	cd $(DBT_DIR) && $(DBT) docs generate $(DBT_FLAGS)

## Lint SQL models
dbt-lint:
	uv run sqlfluff lint $(DBT_DIR)/models/
