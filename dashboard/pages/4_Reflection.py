"""
Streamlit dashboard for apple-health-data
"""

from datetime import datetime

import conf
import streamlit as st
from helpers import (
    load_filtered_s3_data,
    sidebar_date_filter,
)
from kpi import load_kpi_config

# Page configuration
st.set_page_config(
    page_title="🤔 Reflection",
    page_icon="🤔",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🤔 Exercise")


# Sidebar date selection
today = datetime.today().date()
start_date, end_date = sidebar_date_filter()


try:
    filtered_reflections = load_filtered_s3_data(
        conf.key_reflections,
        start_date,
        end_date,
    )
    # Load configuration
    kpi_config = load_kpi_config()

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# ---------------------- AVERAGE activity ----------------------
try:
    st.write(filtered_reflections)
except Exception as e:
    st.error(f"Error computing macro KPIs: {e}")
