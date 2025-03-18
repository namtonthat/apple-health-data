#!/bin/bash

set -e

pushd calendar
uv run python3 lambda.py
pushd
