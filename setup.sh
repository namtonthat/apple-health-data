#!/bin/bash

set -e errexit

echo "create virtual env"
uv venv --python 3.13.1

echo "activating env"
source .venv/bin/activate

echo "syncing"
uv sync
