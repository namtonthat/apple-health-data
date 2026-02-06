"""Exercises page."""

import os
from datetime import date, timedelta
from pathlib import Path

import duckdb
import polars as pl
import streamlit as st

st.set_page_config(page_title="🏋️ Exercises", page_icon="🏋️", layout="wide")

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

# S3 configuration
S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "")
S3_TRANSFORMED_PREFIX = "transformed"

# Big 3 exercises - exact names for 1RM summary display
BIG_3_EXERCISES = {
    "squat": "Squat (Barbell)",
    "bench": "Bench Press (Barbell)",
    "deadlift": "Sumo Deadlift",
}


def calculate_1rm(weight: float, reps: int) -> float | None:
    """Calculate estimated 1RM using Epley formula."""
    if weight is None or reps is None or weight <= 0 or reps <= 0:
        return None
    if reps == 1:
        return weight
    # Epley formula: 1RM = weight × (1 + reps/30)
    return round(weight * (1 + reps / 30), 1)


def get_connection():
    """Get fresh DuckDB connection configured for S3 access."""
    conn = duckdb.connect(":memory:")
    region = "ap-southeast-2"
    access_key = os.environ.get("AWS_ACCESS_KEY_ID", "")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    conn.execute(f"SET s3_region = '{region}'")
    conn.execute(f"SET s3_access_key_id = '{access_key}'")
    conn.execute(f"SET s3_secret_access_key = '{secret_key}'")
    return conn


def get_s3_path(table_name: str) -> str:
    return f"s3://{S3_BUCKET}/{S3_TRANSFORMED_PREFIX}/{table_name}"


def load_workout_sets(start_date: date, end_date: date) -> pl.DataFrame:
    conn = get_connection()
    s3_path = get_s3_path("fct_workout_sets")
    query = f"""
        SELECT
            workout_date,
            workout_name,
            exercise_name,
            set_number,
            weight_kg,
            reps,
            volume_kg,
            rpe,
            set_type,
            started_at,
            exercise_order
        FROM read_parquet('{s3_path}')
        WHERE workout_date BETWEEN ? AND ?
        ORDER BY workout_date DESC, started_at DESC, exercise_order, set_number
    """
    try:
        return pl.from_arrow(conn.execute(query, [start_date, end_date]).fetch_arrow_table())
    except Exception as e:
        if "No files found" in str(e):
            return pl.DataFrame()
        raise


def load_personal_bests() -> dict:
    """Load competition personal bests from OpenPowerlifting data."""
    conn = get_connection()
    s3_path = get_s3_path("fct_personal_bests")
    query = f"""
        SELECT squat_pr_kg, bench_pr_kg, deadlift_pr_kg, total_pr_kg, last_competition
        FROM read_parquet('{s3_path}')
        LIMIT 1
    """
    try:
        result = conn.execute(query).fetchone()
        if result:
            return {
                "squat": result[0],
                "bench": result[1],
                "deadlift": result[2],
                "total": result[3],
                "last_competition": result[4],
            }
    except Exception:
        pass
    return {}


def load_strava_activities(start_date: date, end_date: date) -> pl.DataFrame:
    """Load Strava activities for the date range."""
    conn = get_connection()
    s3_path = get_s3_path("fct_strava_activities")
    query = f"""
        SELECT
            activity_date,
            activity_name,
            activity_type,
            sport_type,
            moving_time_minutes,
            distance_km,
            elevation_gain_m,
            avg_speed_kmh,
            avg_pace_min_per_km,
            avg_heartrate,
            max_heartrate,
            pr_count
        FROM read_parquet('{s3_path}')
        WHERE activity_date BETWEEN ? AND ?
        ORDER BY activity_date DESC
    """
    try:
        return pl.from_arrow(conn.execute(query, [start_date, end_date]).fetch_arrow_table())
    except Exception as e:
        if "No files found" in str(e):
            return pl.DataFrame()
        raise


# Sidebar - Date Filter
st.sidebar.title("Filters")

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
df_exercises = load_workout_sets(start_date, end_date)
competition_prs = load_personal_bests()
df_strava = load_strava_activities(start_date, end_date)

# =============================================================================
# Exercises Section
# =============================================================================
st.header("Exercises")

if df_exercises.height > 0:
    # Add 1RM column for ALL exercises
    df_with_1rm = df_exercises.with_columns(
        pl.struct(["weight_kg", "reps"])
        .map_elements(
            lambda row: calculate_1rm(row["weight_kg"], row["reps"]),
            return_dtype=pl.Float64,
        )
        .alias("est_1rm")
    )

    # Calculate Big 3 1RMs with comparison to competition PRs
    big_3_results = []
    for lift_key, exercise_name in BIG_3_EXERCISES.items():
        lift_data = df_with_1rm.filter(pl.col("exercise_name") == exercise_name)
        if lift_data.height > 0:
            max_1rm = lift_data["est_1rm"].max()
            if max_1rm is not None:
                comp_pr = competition_prs.get(lift_key)
                big_3_results.append((lift_key.title(), max_1rm, comp_pr))

    # Summary metrics + Big 3 on one row with separator
    # 4 summary metrics | 3 Big 3 lifts
    cols = st.columns([1, 1, 1, 1, 0.1, 1, 1, 1])

    with cols[0]:
        n_workouts = df_exercises["workout_date"].n_unique()
        st.metric("Workouts", n_workouts)
    with cols[1]:
        n_exercises = df_exercises["exercise_name"].n_unique()
        st.metric("Exercises", n_exercises)
    with cols[2]:
        total_sets = df_exercises.height
        st.metric("Sets", total_sets)
    with cols[3]:
        total_volume = df_exercises["volume_kg"].sum()
        st.metric("Volume", f"{total_volume:,.0f} kg" if total_volume else "0 kg")

    # Separator
    with cols[4]:
        st.markdown("<div style='border-left: 2px solid #444; height: 80px; margin: 0 auto;'></div>", unsafe_allow_html=True)

    # Big 3 lifts with competition PR comparison
    if len(big_3_results) >= 1:
        with cols[5]:
            name, est_1rm, comp_pr = big_3_results[0]
            delta = f"{est_1rm - comp_pr:+.1f} kg vs {comp_pr:.1f} PR" if comp_pr else None
            st.metric(f"{name} 1RM", f"{est_1rm:.1f} kg", delta=delta)
    if len(big_3_results) >= 2:
        with cols[6]:
            name, est_1rm, comp_pr = big_3_results[1]
            delta = f"{est_1rm - comp_pr:+.1f} kg vs {comp_pr:.1f} PR" if comp_pr else None
            st.metric(f"{name} 1RM", f"{est_1rm:.1f} kg", delta=delta)
    if len(big_3_results) >= 3:
        with cols[7]:
            name, est_1rm, comp_pr = big_3_results[2]
            delta = f"{est_1rm - comp_pr:+.1f} kg vs {comp_pr:.1f} PR" if comp_pr else None
            st.metric(f"{name} 1RM", f"{est_1rm:.1f} kg", delta=delta)

    # Time since last competition badge with OpenPowerlifting link
    last_comp = competition_prs.get("last_competition")
    if last_comp:
        from datetime import datetime
        if isinstance(last_comp, str):
            last_comp_date = datetime.strptime(last_comp[:10], "%Y-%m-%d").date()
        else:
            last_comp_date = last_comp
        days_since = (date.today() - last_comp_date).days
        if days_since < 30:
            time_str = f"{days_since} days"
        elif days_since < 365:
            months = days_since // 30
            time_str = f"{months} month{'s' if months > 1 else ''}"
        else:
            years = days_since // 365
            months = (days_since % 365) // 30
            time_str = f"{years}y {months}m" if months else f"{years} year{'s' if years > 1 else ''}"

        opl_url = os.environ.get("OPENPOWERLIFTING_URL", "")
        if opl_url:
            st.caption(f"⏱️ **{time_str}** since last competition ({last_comp_date.strftime('%b %d, %Y')}) · [OpenPowerlifting Profile]({opl_url})")
        else:
            st.caption(f"⏱️ **{time_str}** since last competition ({last_comp_date.strftime('%b %d, %Y')})")

    st.divider()

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        workouts = ["All"] + sorted(df_exercises["workout_name"].drop_nulls().unique().to_list())
        selected_workout = st.selectbox("Filter by workout", workouts)
    with col2:
        exercises = ["All"] + sorted(df_exercises["exercise_name"].unique().to_list())
        selected_exercise = st.selectbox("Filter by exercise", exercises)

    # Apply filters
    display_df = df_with_1rm
    if selected_workout != "All":
        display_df = display_df.filter(pl.col("workout_name") == selected_workout)
    if selected_exercise != "All":
        display_df = display_df.filter(pl.col("exercise_name") == selected_exercise)

    # Create color mapping for workouts (font colors for seamless look)
    unique_workouts = display_df["workout_name"].drop_nulls().unique().to_list()
    workout_colors = [
        "#E63946", "#2A9D8F", "#E76F51", "#457B9D", "#8338EC",
        "#06D6A0", "#F72585", "#4361EE", "#FB8500", "#7209B7",
    ]

    # Convert to pandas for display with styling
    display_pd = display_df.to_pandas()

    # Style function for workout column - font color only
    def color_workout(val):
        if val is None or val not in unique_workouts:
            return ""
        idx = unique_workouts.index(val) % len(workout_colors)
        return f"color: {workout_colors[idx]}; font-weight: 600;"

    # Apply styling
    styled_df = display_pd.style.map(color_workout, subset=["workout_name"])

    # Display table
    st.dataframe(
        styled_df,
        column_config={
            "workout_date": st.column_config.DateColumn("Date", width="small"),
            "workout_name": st.column_config.TextColumn("Workout", width="medium"),
            "exercise_name": st.column_config.TextColumn("Exercise", width="medium"),
            "set_number": st.column_config.NumberColumn("Set", width="small"),
            "weight_kg": st.column_config.NumberColumn("Weight (kg)", format="%.1f", width="small"),
            "reps": st.column_config.NumberColumn("Reps", width="small"),
            "est_1rm": st.column_config.NumberColumn(
                "Est 1RM",
                format="%.1f kg",
                width="small",
                help="Estimated 1 Rep Max (Epley formula)",
            ),
            "volume_kg": st.column_config.NumberColumn("Volume", format="%.0f", width="small"),
            "rpe": st.column_config.NumberColumn("RPE", format="%.1f", width="small"),
            "set_type": st.column_config.TextColumn("Type", width="small"),
        },
        column_order=["workout_date", "workout_name", "exercise_name", "set_number",
                      "weight_kg", "reps", "est_1rm", "volume_kg", "rpe", "set_type"],
        hide_index=True,
        width="stretch",
    )
else:
    st.info("No workout data available for selected period")

# =============================================================================
# Strava Activities Section
# =============================================================================
st.divider()
st.header("🏃 Strava Activities")

if df_strava.height > 0:
    # Activity type icons
    ACTIVITY_ICONS = {
        "Run": "🏃",
        "Ride": "🚴",
        "Swim": "🏊",
        "Walk": "🚶",
        "Hike": "🥾",
        "Workout": "💪",
        "WeightTraining": "🏋️",
        "Yoga": "🧘",
    }

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        n_activities = df_strava.height
        st.metric("Activities", n_activities)
    with col2:
        total_distance = df_strava["distance_km"].sum()
        st.metric("Distance", f"{total_distance:.1f} km" if total_distance else "0 km")
    with col3:
        total_time = df_strava["moving_time_minutes"].sum()
        hours = int(total_time // 60) if total_time else 0
        mins = int(total_time % 60) if total_time else 0
        st.metric("Time", f"{hours}h {mins}m")
    with col4:
        total_elevation = df_strava["elevation_gain_m"].sum()
        st.metric("Elevation", f"{total_elevation:,.0f} m" if total_elevation else "0 m")

    # Filter by activity type
    activity_types = ["All"] + sorted(df_strava["activity_type"].drop_nulls().unique().to_list())
    selected_type = st.selectbox("Filter by activity type", activity_types)

    display_strava = df_strava
    if selected_type != "All":
        display_strava = display_strava.filter(pl.col("activity_type") == selected_type)

    # Add icon column
    display_strava = display_strava.with_columns(
        pl.col("activity_type").replace(ACTIVITY_ICONS, default="🏅").alias("icon")
    )

    # Format pace as MM:SS
    def format_pace(pace_decimal):
        if pace_decimal is None or pace_decimal <= 0:
            return "-"
        mins = int(pace_decimal)
        secs = int((pace_decimal - mins) * 60)
        return f"{mins}:{secs:02d}"

    display_strava = display_strava.with_columns(
        pl.col("avg_pace_min_per_km")
        .map_elements(format_pace, return_dtype=pl.Utf8)
        .alias("pace_formatted")
    )

    # Display table
    st.dataframe(
        display_strava.to_pandas(),
        column_config={
            "icon": st.column_config.TextColumn("", width="small"),
            "activity_date": st.column_config.DateColumn("Date", width="small"),
            "activity_name": st.column_config.TextColumn("Activity", width="medium"),
            "activity_type": st.column_config.TextColumn("Type", width="small"),
            "moving_time_minutes": st.column_config.NumberColumn("Time (min)", format="%.0f", width="small"),
            "distance_km": st.column_config.NumberColumn("Distance (km)", format="%.2f", width="small"),
            "pace_formatted": st.column_config.TextColumn("Pace (/km)", width="small"),
            "elevation_gain_m": st.column_config.NumberColumn("Elevation (m)", format="%.0f", width="small"),
            "avg_heartrate": st.column_config.NumberColumn("Avg HR", format="%.0f", width="small"),
            "max_heartrate": st.column_config.NumberColumn("Max HR", format="%.0f", width="small"),
            "pr_count": st.column_config.NumberColumn("PRs", width="small"),
        },
        column_order=["icon", "activity_date", "activity_name", "activity_type",
                      "moving_time_minutes", "distance_km", "pace_formatted",
                      "elevation_gain_m", "avg_heartrate", "max_heartrate", "pr_count"],
        hide_index=True,
        width="stretch",
    )
else:
    st.info("No Strava activities available for selected period. Add STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, and STRAVA_REFRESH_TOKEN to .env to enable.")
