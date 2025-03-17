#!/bin/bash

set -e errexit
# apply infra changes
source .venv/bin/activate

pushd calendar
python3 lambda.py
pushd
