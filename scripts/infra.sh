#!/bin/bash

set -e

echo "running infra changes"
pushd infra

echo "deploying infra"
tofu init --upgrade

echo "planning"
tofu plan

echo "applying"
tofu apply -auto-approve
