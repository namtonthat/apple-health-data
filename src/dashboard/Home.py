"""
Health & Fitness Dashboard - Home

Main entry point for the Streamlit dashboard.
"""

import os
from pathlib import Path

import streamlit as st

# Page config
st.set_page_config(
    page_title="🏠 Home",
    page_icon="🏠",
    layout="wide",
)

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Get user name from environment
USER_NAME = os.environ.get("USER_NAME", "there")

# Main content - Home page
st.title(f"👋 Welcome, {USER_NAME}!")

st.markdown("""
Your personal health and fitness dashboard, powered by Apple Health, Hevy, and Strava.
""")

st.divider()

# Navigation cards with links
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 😴 Recovery & Health

    Track your sleep patterns, nutrition, and daily macros.

    - Sleep duration and stages (Deep, REM, Light)
    - Macro tracking with goals (Protein, Carbs, Fat)
    - Calorie balance (Activity vs Eaten)
    """)
    st.page_link("pages/1_Recovery_&_Health.py", label="Go to Recovery & Health →", icon="😴")

with col2:
    st.markdown("""
    ### 🏋️ Exercises

    Monitor your workouts and cardio activities.

    - Workout logs with sets, reps, and volume (Hevy)
    - Estimated 1RM for Big 3 lifts
    - Runs, rides, and swims (Strava)
    """)
    st.page_link("pages/2_Exercises.py", label="Go to Exercises →", icon="🏋️")

st.divider()

st.markdown("""
### 📊 Data Sources

| Source | Data |
|--------|------|
| 🍎 Apple Health | Sleep, activity, vitals |
| 📱 Nutrition App | Nutrition & macros (via Apple Health) |
| 💪 Hevy | Workout logs |
| 🏃 Strava | Runs, rides, swims |
""")
