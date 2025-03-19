"""
Dashboard application using Reflex.

This application visualizes sleep and macros data read from AWS S3,
and allows the user to submit a weekly reflection (5 questions) which is stored in DuckDB.
It also provides functionality to filter the data by week.
"""

import logging
from datetime import datetime

import conf
import streamlit as st
from helpers import (
    insert_reflections_into_duckdb,
    load_reflections_from_duckdb,
    read_parquet_from_s3,
)

# Configure logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.title("Health Dashboard")

# --- Display Sleep Data ---
st.header("Sleep Data")
try:
    sleep_df = read_parquet_from_s3(conf.s3_bucket, conf.key_sleep)
    st.dataframe(sleep_df.to_pandas())
except Exception as e:
    st.error(f"Error loading sleep data: {e}")

# --- Display Macros Data ---
st.header("Macros Data")
try:
    macros_df = read_parquet_from_s3(conf.s3_bucket, conf.key_macros)
    st.dataframe(macros_df.to_pandas())
except Exception as e:
    st.error(f"Error loading macros data: {e}")

# --- Reflection Form ---
st.header("Weekly Reflection")
with st.form("reflection_form"):
    q1 = st.text_input("How was your mood?")
    q2 = st.text_input("Energy level?")
    q3 = st.text_input("Stress level?")
    q4 = st.text_input("Productivity?")
    q5 = st.text_input("Overall feeling?")
    submit = st.form_submit_button("Submit Reflection")

if submit:
    new_entry = {
        "week": datetime.now().strftime("%Y-%W"),
        "q1": q1,
        "q2": q2,
        "q3": q3,
        "q4": q4,
        "q5": q5,
        "timestamp": datetime.now().isoformat(),
    }
    try:
        insert_reflections_into_duckdb(conf.duckdb_path, new_entry)
        st.success("Reflection submitted!")
    except Exception as e:
        st.error(f"Error submitting reflection: {e}")

# --- Display Reflection Data ---
st.header("Reflection Data")
try:
    reflections_df = load_reflections_from_duckdb(conf.duckdb_path)
    st.dataframe(reflections_df.to_pandas())
except Exception as e:
    st.error(f"Error loading reflections: {e}")
