"""Exercises page."""

import os
from datetime import date, timedelta
from pathlib import Path

import duckdb
import polars as pl
import streamlit as st

st.set_page_config(page_title="Exercises", page_icon="🏋️", layout="wide")

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


@st.cache_resource
def get_connection():
    """Get DuckDB connection configured for S3 access."""
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

    # Calculate Big 3 1RMs
    big_3_results = []
    for lift_key, exercise_name in BIG_3_EXERCISES.items():
        lift_data = df_with_1rm.filter(pl.col("exercise_name") == exercise_name)
        if lift_data.height > 0:
            max_1rm = lift_data["est_1rm"].max()
            if max_1rm is not None:
                big_3_results.append((lift_key.title(), max_1rm))

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

    # Big 3 lifts
    if len(big_3_results) >= 1:
        with cols[5]:
            st.metric(f"{big_3_results[0][0]} 1RM", f"{big_3_results[0][1]:.1f} kg")
    if len(big_3_results) >= 2:
        with cols[6]:
            st.metric(f"{big_3_results[1][0]} 1RM", f"{big_3_results[1][1]:.1f} kg")
    if len(big_3_results) >= 3:
        with cols[7]:
            st.metric(f"{big_3_results[2][0]} 1RM", f"{big_3_results[2][1]:.1f} kg")

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
        use_container_width=True,
    )
else:
    st.info("No workout data available for selected period")
