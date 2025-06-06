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

if [ "$GITHUB_ACTIONS" = "true" ]; then
  echo "Detected GitHub Actions environment. Not outputting secret access key"
else
  echo "showing the github_actions secret access key"
  tofu output -raw github_actions_secret_access_key
  echo

  echo "showing the streamlit secret access key"
  tofu output -raw streamlit_secret_access_key
  # Require a new line to avoid printing out the %
  echo
fi
