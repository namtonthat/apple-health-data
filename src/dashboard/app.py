"""
Health & Fitness Dashboard

Streamlit dashboard for visualizing health data from Apple Health
and workout data from Hevy.
"""

from datetime import date, timedelta
from pathlib import Path

import duckdb
import streamlit as st

# Page config
st.set_page_config(
    page_title="Health Dashboard",
    page_icon="💪",
    layout="wide",
)

# Database connection
DB_PATH = Path(__file__).parent.parent.parent / "dbt_project" / "hevy.duckdb"


@st.cache_resource
def get_connection():
    """Get DuckDB connection."""
    return duckdb.connect(str(DB_PATH), read_only=True)


def load_daily_summary(start_date: date, end_date: date):
    """Load daily summary data for date range."""
    conn = get_connection()
    query = """
        SELECT *
        FROM main_marts.fct_daily_summary
        WHERE date BETWEEN ? AND ?
        ORDER BY date
    """
    return conn.execute(query, [start_date, end_date]).fetchdf()


def load_workout_sets(start_date: date, end_date: date):
    """Load workout sets for date range."""
    conn = get_connection()
    query = """
        SELECT
            workout_date,
            exercise_name,
            set_number,
            weight_kg,
            reps,
            volume_kg,
            rpe,
            set_type
        FROM main_marts.fct_workout_sets
        WHERE workout_date BETWEEN ? AND ?
        ORDER BY workout_date DESC, exercise_name, set_number
    """
    return conn.execute(query, [start_date, end_date]).fetchdf()


# Sidebar - Date Filter
st.sidebar.title("Filters")

# Quick date range presets
preset = st.sidebar.radio(
    "Date Range",
    ["Last 7 days", "Last 30 days", "This month", "Custom"],
    index=0,
)

today = date.today()
if preset == "Last 7 days":
    start_date = today - timedelta(days=7)
    end_date = today
elif preset == "Last 30 days":
    start_date = today - timedelta(days=30)
    end_date = today
elif preset == "This month":
    start_date = today.replace(day=1)
    end_date = today
else:
    start_date = st.sidebar.date_input("Start date", today - timedelta(days=7))
    end_date = st.sidebar.date_input("End date", today)

st.sidebar.markdown(f"**Showing:** {start_date} to {end_date}")

# Load data
df_daily = load_daily_summary(start_date, end_date)
df_exercises = load_workout_sets(start_date, end_date)

# Main content
st.title("Health & Fitness Dashboard")

# Sleep Section
st.header("Sleep")

if "sleep_hours" in df_daily.columns and df_daily["sleep_hours"].notna().any():
    sleep_data = df_daily[df_daily["sleep_hours"].notna()]

    # Metric cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_sleep = sleep_data["sleep_hours"].mean()
        st.metric("Avg Sleep", f"{avg_sleep:.1f}h" if avg_sleep else "-")
    with col2:
        avg_deep = sleep_data["sleep_deep_hours"].mean()
        st.metric("Avg Deep", f"{avg_deep:.1f}h" if avg_deep else "-")
    with col3:
        avg_rem = sleep_data["sleep_rem_hours"].mean()
        st.metric("Avg REM", f"{avg_rem:.1f}h" if avg_rem else "-")
    with col4:
        avg_light = sleep_data["sleep_light_hours"].mean()
        st.metric("Avg Light", f"{avg_light:.1f}h" if avg_light else "-")

    # Sleep trend chart
    if len(sleep_data) > 1:
        st.line_chart(
            sleep_data.set_index("date")[
                ["sleep_hours", "sleep_deep_hours", "sleep_rem_hours", "sleep_light_hours"]
            ],
            color=["#636EFA", "#00CC96", "#AB63FA", "#FFA15A"],
        )
else:
    st.info("No sleep data available for selected period")

st.divider()

# Calories & Macros Section
st.header("Calories & Macros")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Calories Burned")
    if "total_calories" in df_daily.columns and df_daily["total_calories"].notna().any():
        cal_data = df_daily[df_daily["total_calories"].notna()]

        c1, c2, c3 = st.columns(3)
        with c1:
            avg_active = cal_data["active_calories"].mean()
            st.metric("Avg Active", f"{avg_active:,.0f}" if avg_active else "-")
        with c2:
            avg_basal = cal_data["basal_calories"].mean()
            st.metric("Avg Basal", f"{avg_basal:,.0f}" if avg_basal else "-")
        with c3:
            avg_total = cal_data["total_calories"].mean()
            st.metric("Avg Total", f"{avg_total:,.0f}" if avg_total else "-")

        if len(cal_data) > 1:
            st.area_chart(
                cal_data.set_index("date")[["active_calories", "basal_calories"]],
                color=["#EF553B", "#636EFA"],
            )
    else:
        st.info("No calorie data available")

with col2:
    st.subheader("Macros")
    has_macros = (
        "protein_g" in df_daily.columns
        and df_daily["protein_g"].notna().any()
    )

    if has_macros:
        macro_data = df_daily[df_daily["protein_g"].notna()]

        c1, c2, c3 = st.columns(3)
        with c1:
            avg_protein = macro_data["protein_g"].mean()
            st.metric("Avg Protein", f"{avg_protein:.0f}g" if avg_protein else "-")
        with c2:
            avg_carbs = macro_data["carbs_g"].mean()
            st.metric("Avg Carbs", f"{avg_carbs:.0f}g" if avg_carbs else "-")
        with c3:
            avg_fat = macro_data["fat_g"].mean()
            st.metric("Avg Fat", f"{avg_fat:.0f}g" if avg_fat else "-")

        if len(macro_data) > 1:
            st.bar_chart(
                macro_data.set_index("date")[["protein_g", "carbs_g", "fat_g"]],
                color=["#00CC96", "#FFA15A", "#EF553B"],
            )
    else:
        st.info("No macro data available - log food in an app that syncs to Apple Health")

st.divider()

# Exercises Section
st.header("Exercises")

if not df_exercises.empty:
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        n_workouts = df_exercises["workout_date"].nunique()
        st.metric("Workouts", n_workouts)
    with col2:
        n_exercises = df_exercises["exercise_name"].nunique()
        st.metric("Unique Exercises", n_exercises)
    with col3:
        total_sets = len(df_exercises)
        st.metric("Total Sets", total_sets)
    with col4:
        total_volume = df_exercises["volume_kg"].sum()
        st.metric("Total Volume", f"{total_volume:,.0f} kg")

    # Exercise filter
    exercises = ["All"] + sorted(df_exercises["exercise_name"].unique().tolist())
    selected_exercise = st.selectbox("Filter by exercise", exercises)

    if selected_exercise != "All":
        display_df = df_exercises[df_exercises["exercise_name"] == selected_exercise]
    else:
        display_df = df_exercises

    # Display table
    st.dataframe(
        display_df,
        column_config={
            "workout_date": st.column_config.DateColumn("Date"),
            "exercise_name": "Exercise",
            "set_number": "Set",
            "weight_kg": st.column_config.NumberColumn("Weight (kg)", format="%.1f"),
            "reps": "Reps",
            "volume_kg": st.column_config.NumberColumn("Volume (kg)", format="%.0f"),
            "rpe": st.column_config.NumberColumn("RPE", format="%.1f"),
            "set_type": "Type",
        },
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("No workout data available for selected period")
