#!/bin/bash

set -e errexit

source .venv/bin/activate
echo "running dashboard"
pushd dashboard
# streamlit run main.py
streamlit run 0_🏠_Home.py
