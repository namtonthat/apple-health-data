#!/bin/bash

set -e

echo "running infra changes"
pushd infra

echo "deploying infra"
tofu init --upgrade

echo "planning"
tofu plan

echo "applying"
if [ "$GITHUB_ACTIONS" = "true" ]; then
  echo "Detected GitHub Actions environment. Setting show_sensitive_outputs to false."
  tofu apply -auto-approve -var="show_sensitive_outputs=false"
else
  tofu apply -auto-approve

  echo "showing the github_actions secret access key"
  tofu output -raw github_actions_secret_access_key
fi
