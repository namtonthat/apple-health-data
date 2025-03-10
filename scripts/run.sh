#!/bin/bash

set -e errexit

echo "activate env"
source .venv/bin/activate

echo "running infra changes"
pushd lambda

# dbt run
#
echo "deploying infra"
tofu init --upgrade

echo "planning"
tofu plan

# echo "applying"
# tofu apply -auto-approve
