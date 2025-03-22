#!/bin/bash

set -e errexit

source .venv/bin/activate
echo "running dashboard"
pushd dashboard
streamlit run main.py
