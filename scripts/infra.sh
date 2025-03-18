#!/bin/bash

set -e

echo "activate env"
source .venv/bin/activate

echo "running infra changes"
pushd infra

# dbt run
echo "deploying infra"
tofu init --upgrade

echo "planning"
tofu plan

echo "run podman"
podman machine init
podman machine start

echo "applying"
tofu apply -auto-approve
