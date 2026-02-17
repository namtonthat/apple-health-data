"""
Health & Fitness Dashboard - Home

Main entry point for the Streamlit dashboard.
"""

import streamlit as st

# Page config
st.set_page_config(
    page_title="🏠 Home",
    page_icon="🏠",
    layout="wide",
)

from dashboard.config import LAST_UPDATED, USER_NAME

# Main content - Home page
st.title(f"👋 Welcome to {USER_NAME}'s Health & Fitness Dashboard")
st.caption(f"Last updated: {LAST_UPDATED}")

st.markdown("""
A personal dashboard powered by Apple Health, Hevy, and Strava.
""")

st.divider()

# Navigation cards with links
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 😴 Recovery

    Track your sleep patterns and mindfulness.

    - Sleep duration and stages (Deep, REM, Light)
    - Meditation minutes with daily goals
    """)
    st.page_link("pages/1_Recovery.py", label="Go to Recovery →", icon="😴")

with col2:
    st.markdown("""
    ### 🚶 Activity

    Monitor your daily movement.

    - Daily step count with goal tracking
    """)
    st.page_link("pages/2_Activity.py", label="Go to Activity →", icon="🚶")

col3, col4 = st.columns(2)

with col3:
    st.markdown("""
    ### 🍽️ Nutrition & Body

    Track your macros, calories, and weight.

    - Macro tracking with goals (Protein, Carbs, Fat)
    - Weight trend and body composition
    """)
    st.page_link("pages/3_Nutrition_&_Body.py", label="Go to Nutrition & Body →", icon="🍽️")

with col4:
    st.markdown("""
    ### 🏋️ Exercises

    Monitor your workouts and cardio activities.

    - Workout logs with sets, reps, and volume (Hevy)
    - Estimated 1RM for Big 3 lifts
    - Runs, rides, and swims (Strava)
    """)
    st.page_link("pages/4_Exercises.py", label="Go to Exercises →", icon="🏋️")

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
