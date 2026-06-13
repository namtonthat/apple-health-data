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
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 😴 Recovery

    Track your sleep, mindfulness, and movement.

    - Sleep duration and stages (Deep, REM, Light)
    - Meditation minutes with daily goals
    - Daily step count with goal tracking
    """)
    st.page_link("pages/1_Recovery.py", label="Go to Recovery →", icon="😴")

with col2:
    st.markdown("""
    ### 🍽️ Nutrition & Body

    Track your macros, calories, and weight.

    - Macro tracking with goals (Protein, Carbs, Fat)
    - Weight trend and body composition
    """)
    st.page_link("pages/2_Nutrition_&_Body.py", label="Go to Nutrition & Body →", icon="🍽️")

with col3:
    st.markdown("""
    ### 🏋️ Exercises

    Monitor your workouts and cardio activities.

    - Workout logs with sets, reps, and volume (Hevy)
    - Estimated 1RM for Big 3 lifts
    - Rolling e1RM total trend
    - Runs, rides, and swims (Strava)
    """)
    st.page_link("pages/3_Exercises.py", label="Go to Exercises →", icon="🏋️")

col4, _, _ = st.columns(3)
with col4:
    st.markdown("""
    ### 📊 Performance Insights

    See how recovery and nutrition relate to training.

    - Sleep, HRV & fuel vs training-day performance
    - Training load vs next-day recovery
    - Long-run weight, calorie, and sleep trends
    """)
    st.page_link("pages/4_Performance_Insights.py", label="Go to Performance Insights →", icon="📊")

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
