#!/bin/bash

# apply infra changes
source .venv/bin/activate

# wipe aws s3
# aws s3 rm s3://api-health-data-ntonthat/landing/ --recursive

pushd infra
tofu apply -auto-approve
popd

pushd transforms
dbt run
duckdb dbt.duckdb
