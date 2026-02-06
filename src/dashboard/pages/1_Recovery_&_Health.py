"""Recovery & Health page."""

import os
import tomllib
from datetime import date, timedelta
from pathlib import Path

import altair as alt
import duckdb
import polars as pl
import streamlit as st

st.set_page_config(page_title="😴 Recovery & Health", page_icon="😴", layout="wide")

# Load secrets from .env for local development
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")


def get_secret(key: str, default: str = "") -> str:
    """Get secret from st.secrets (Streamlit Cloud) or env vars (local)."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.environ.get(key, default)


def load_config() -> dict:
    """Load non-sensitive config from pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
    return pyproject.get("tool", {}).get("dashboard", {})


# Load config
CONFIG = load_config()

# S3 configuration (from pyproject.toml)
S3_BUCKET = CONFIG.get("s3_bucket_name", "")
S3_TRANSFORMED_PREFIX = CONFIG.get("s3_transformed_prefix", "transformed")
AWS_REGION = CONFIG.get("aws_region", "ap-southeast-2")

# Goals from config (with defaults)
goals_config = CONFIG.get("goals", {})
GOALS = {
    "sleep_hours": goals_config.get("sleep_hours", 7.0),
    "sleep_deep_hours": goals_config.get("sleep_deep_hours", 1.5),
    "sleep_rem_hours": goals_config.get("sleep_rem_hours", 1.5),
    "sleep_light_hours": goals_config.get("sleep_light_hours", 3.5),
    "protein_g": goals_config.get("protein_g", 170.0),
    "carbs_g": goals_config.get("carbs_g", 300.0),
    "fat_g": goals_config.get("fat_g", 60.0),
    "steps": goals_config.get("steps", 10000),
}


def metric_with_goal(
    label: str,
    value: float | None,
    goal: float | None = None,
    unit: str = "",
    fmt: str = ".1f",
    inverse: bool = False,
) -> None:
    """Display a metric with optional goal delta.

    Args:
        label: Metric label
        value: Current value
        goal: Target goal (if None, no delta shown)
        unit: Unit suffix (e.g., "h", "g")
        fmt: Format string for numbers
        inverse: If True, lower is better (delta color inverted)
    """
    if value is None:
        st.metric(label, "-")
        return

    display_value = f"{value:{fmt}}{unit}"

    if goal is not None:
        delta = value - goal
        delta_str = f"{delta:+{fmt}}{unit} vs {goal:{fmt}}{unit} goal"
        # For sleep/protein/carbs: higher is better (delta_color normal)
        # For fat: could go either way, keeping normal for now
        delta_color = "inverse" if inverse else "normal"
        st.metric(label, display_value, delta=delta_str, delta_color=delta_color)
    else:
        st.metric(label, display_value)


def get_connection():
    """Get fresh DuckDB connection configured for S3 access."""
    conn = duckdb.connect(":memory:")
    access_key = get_secret("AWS_ACCESS_KEY_ID")
    secret_key = get_secret("AWS_SECRET_ACCESS_KEY")
    conn.execute(f"SET s3_region = '{AWS_REGION}'")
    conn.execute(f"SET s3_access_key_id = '{access_key}'")
    conn.execute(f"SET s3_secret_access_key = '{secret_key}'")
    return conn


def get_s3_path(table_name: str) -> str:
    return f"s3://{S3_BUCKET}/{S3_TRANSFORMED_PREFIX}/{table_name}"


@st.cache_data(ttl=timedelta(hours=1), show_spinner="Loading health data...")
def load_recent_summary() -> pl.DataFrame:
    """Load the full 90-day recent table (cached across reruns)."""
    conn = get_connection()
    s3_path = get_s3_path("fct_daily_summary_recent")
    query = f"""
        SELECT *
        FROM read_parquet('{s3_path}')
        ORDER BY date
    """
    try:
        return pl.from_arrow(conn.execute(query).fetch_arrow_table())
    except Exception as e:
        if "No files found" in str(e):
            return pl.DataFrame()
        raise


def load_daily_summary(start_date: date, end_date: date) -> pl.DataFrame:
    """Load daily summary from the recent (90-day) table with date range."""
    conn = get_connection()
    s3_path = get_s3_path("fct_daily_summary_recent")
    query = f"""
        SELECT *
        FROM read_parquet('{s3_path}')
        WHERE date BETWEEN ? AND ?
        ORDER BY date
    """
    try:
        return pl.from_arrow(conn.execute(query, [start_date, end_date]).fetch_arrow_table())
    except Exception as e:
        if "No files found" in str(e):
            return pl.DataFrame()
        raise


# Sidebar - Date Filter
st.sidebar.title("Filters")

MAX_LOOKBACK = 90
earliest_allowed = date.today() - timedelta(days=MAX_LOOKBACK)

preset = st.sidebar.radio(
    "Date Range",
    ["Last 7 days", "Last 30 days", "Last 90 days", "This month", "Custom"],
    index=0,
)

today = date.today()
if preset == "Last 7 days":
    start_date = today - timedelta(days=7)
    end_date = today
elif preset == "Last 30 days":
    start_date = today - timedelta(days=30)
    end_date = today
elif preset == "Last 90 days":
    start_date = today - timedelta(days=90)
    end_date = today
elif preset == "This month":
    start_date = today.replace(day=1)
    end_date = today
else:
    start_date = st.sidebar.date_input(
        "Start date", today - timedelta(days=7), min_value=earliest_allowed,
    )
    end_date = st.sidebar.date_input("End date", today)

st.sidebar.markdown(f"**Showing:** {start_date} to {end_date}")

# Load data — use cached table for presets, fresh query for custom
if preset != "Custom":
    df_all = load_recent_summary()
    if df_all.height > 0 and "date" in df_all.columns:
        df_daily = df_all.filter(
            (pl.col("date") >= pl.lit(start_date)) & (pl.col("date") <= pl.lit(end_date))
        )
    else:
        df_daily = df_all
else:
    df_daily = load_daily_summary(start_date, end_date)

# =============================================================================
# Sleep Section
# =============================================================================
st.header("Sleep")

if "sleep_hours" in df_daily.columns and df_daily["sleep_hours"].drop_nulls().len() > 0:
    sleep_data = df_daily.filter(pl.col("sleep_hours").is_not_null())

    # Metric cards with goals
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        metric_with_goal("Sleep", sleep_data["sleep_hours"].mean(), GOALS["sleep_hours"], "h")
    with col2:
        metric_with_goal("Deep", sleep_data["sleep_deep_hours"].mean(), GOALS["sleep_deep_hours"], "h")
    with col3:
        metric_with_goal("REM", sleep_data["sleep_rem_hours"].mean(), GOALS["sleep_rem_hours"], "h")
    with col4:
        metric_with_goal("Light", sleep_data["sleep_light_hours"].mean(), GOALS["sleep_light_hours"], "h")
    with col5:
        days_hit = sleep_data.filter(pl.col("sleep_hours") >= GOALS["sleep_hours"]).height
        total_days = sleep_data.height
        st.metric("Days at Goal", f"{days_hit} / {total_days}")

    # Sleep bar chart by date with labels
    if sleep_data.height > 0:
        sleep_chart_data = (
            sleep_data
            .with_columns(pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("Date"))
            .select(["Date", "sleep_deep_hours", "sleep_rem_hours", "sleep_light_hours", "sleep_hours"])
            .to_pandas()
        )

        # Melt for stacked bar chart
        sleep_melted = sleep_chart_data.melt(
            id_vars=["Date", "sleep_hours"],
            value_vars=["sleep_deep_hours", "sleep_rem_hours", "sleep_light_hours"],
            var_name="Stage",
            value_name="Hours"
        )
        sleep_melted["Stage"] = sleep_melted["Stage"].map({
            "sleep_deep_hours": "Deep",
            "sleep_rem_hours": "REM",
            "sleep_light_hours": "Light"
        })

        # Stacked bar chart
        bars = alt.Chart(sleep_melted).mark_bar().encode(
            x=alt.X("Date:N", sort=None, title="Date"),
            y=alt.Y("Hours:Q", title="Hours"),
            color=alt.Color("Stage:N", scale=alt.Scale(
                domain=["Deep", "REM", "Light"],
                range=["#1f77b4", "#9467bd", "#ff7f0e"]
            )),
            order=alt.Order("Stage:N", sort="descending")
        )

        # Total label on top of each bar
        totals = sleep_chart_data[["Date", "sleep_hours"]].drop_duplicates()
        text = alt.Chart(totals).mark_text(dy=-10, fontSize=12, fontWeight="bold").encode(
            x=alt.X("Date:N", sort=None),
            y=alt.Y("sleep_hours:Q"),
            text=alt.Text("sleep_hours:Q", format=".1f")
        )

        st.altair_chart(bars + text, width="stretch")
else:
    st.info("No sleep data available for selected period")

st.divider()

# =============================================================================
# Steps Section
# =============================================================================
st.header("Steps")

has_steps = "steps" in df_daily.columns and df_daily["steps"].drop_nulls().len() > 0

if has_steps:
    steps_data = df_daily.filter(pl.col("steps").is_not_null())

    # Metric cards
    col1, col2, col3 = st.columns(3)
    with col1:
        metric_with_goal("Daily Avg", steps_data["steps"].mean(), GOALS["steps"], "", ",.0f")
    with col2:
        metric_with_goal("Best Day", steps_data["steps"].max(), unit="", fmt=",.0f")
    with col3:
        days_hit = steps_data.filter(pl.col("steps") >= GOALS["steps"]).height
        total_days = steps_data.height
        st.metric("Days at Goal", f"{days_hit} / {total_days}")

    # Steps bar chart
    if steps_data.height > 0:
        steps_chart_data = (
            steps_data
            .with_columns(pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("Date"))
            .select(["Date", "steps"])
            .to_pandas()
        )

        bars = alt.Chart(steps_chart_data).mark_bar().encode(
            x=alt.X("Date:N", sort=None, title="Date"),
            y=alt.Y("steps:Q", title="Steps"),
            color=alt.condition(
                alt.datum.steps >= GOALS["steps"],
                alt.value("#00CC96"),
                alt.value("#636EFA"),
            ),
        )

        # Goal line
        goal_line = alt.Chart(steps_chart_data).mark_rule(
            color="#ff6b6b", strokeDash=[5, 5], strokeWidth=2
        ).encode(y=alt.datum(GOALS["steps"]))

        # Labels on top of bars
        text = alt.Chart(steps_chart_data).mark_text(
            dy=-10, fontSize=11, fontWeight="bold"
        ).encode(
            x=alt.X("Date:N", sort=None),
            y=alt.Y("steps:Q"),
            text=alt.Text("steps:Q", format=",.0f"),
        )

        st.altair_chart(bars + goal_line + text, width="stretch")
else:
    st.info("No step data available for selected period")

st.divider()

# =============================================================================
# Calories & Macros Section
# =============================================================================
st.header("Calories & Macros")

has_calories = "total_calories" in df_daily.columns and df_daily["total_calories"].drop_nulls().len() > 0
has_macros = "protein_g" in df_daily.columns and df_daily["protein_g"].drop_nulls().len() > 0

if has_calories or has_macros:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Calories")
        if has_calories:
            cal_data = df_daily.filter(pl.col("total_calories").is_not_null())
            c1, c2, c3 = st.columns(3)
            with c1:
                metric_with_goal("Activity", cal_data["calculated_calories"].mean(), fmt=",.0f")
            with c2:
                metric_with_goal("Eaten", cal_data["logged_calories"].mean(), fmt=",.0f")
            with c3:
                metric_with_goal("Total", cal_data["total_calories"].mean(), fmt=",.0f")
        else:
            st.info("No calorie data available")

    with col2:
        st.subheader("Macros (Avg)")
        if has_macros:
            macro_data = df_daily.filter(pl.col("protein_g").is_not_null())
            c1, c2, c3 = st.columns(3)
            with c1:
                metric_with_goal("Protein", macro_data["protein_g"].mean(), GOALS["protein_g"], "g", ".0f")
            with c2:
                metric_with_goal("Carbs", macro_data["carbs_g"].mean(), GOALS["carbs_g"], "g", ".0f")
            with c3:
                metric_with_goal("Fat", macro_data["fat_g"].mean(), GOALS["fat_g"], "g", ".0f")
        else:
            st.info("No macro data available")

    # Macros and Weight charts side by side (Macros left, Weight right)
    has_weight = "weight_kg" in df_daily.columns and df_daily["weight_kg"].drop_nulls().len() > 0

    chart_col1, divider_col, chart_col2 = st.columns([1, 0.05, 1])

    with chart_col1:
        st.subheader("Daily Macros (g)")
        if has_macros:
            macro_data = df_daily.filter(pl.col("protein_g").is_not_null())
            if macro_data.height > 0:
                macro_chart_data = (
                    macro_data
                    .with_columns([
                        pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("Date"),
                        (pl.col("protein_g") + pl.col("carbs_g") + pl.col("fat_g")).alias("total_macros")
                    ])
                    .select(["Date", "protein_g", "carbs_g", "fat_g", "total_macros"])
                    .to_pandas()
                )

                macro_melted = macro_chart_data.melt(
                    id_vars=["Date", "total_macros"],
                    value_vars=["protein_g", "carbs_g", "fat_g"],
                    var_name="Macro",
                    value_name="Grams"
                )
                macro_melted["Macro"] = macro_melted["Macro"].map({
                    "protein_g": "Protein",
                    "carbs_g": "Carbs",
                    "fat_g": "Fat"
                })

                bars = alt.Chart(macro_melted).mark_bar().encode(
                    x=alt.X("Date:N", sort=None, title="Date"),
                    y=alt.Y("Grams:Q", title="Grams"),
                    color=alt.Color("Macro:N", scale=alt.Scale(
                        domain=["Protein", "Carbs", "Fat"],
                        range=["#00CC96", "#FFA15A", "#EF553B"]
                    )),
                    order=alt.Order("Macro:N", sort="descending")
                )

                totals = macro_chart_data[["Date", "total_macros"]].drop_duplicates()
                text = alt.Chart(totals).mark_text(dy=-10, fontSize=12, fontWeight="bold").encode(
                    x=alt.X("Date:N", sort=None),
                    y=alt.Y("total_macros:Q"),
                    text=alt.Text("total_macros:Q", format=".0f")
                )

                st.altair_chart(bars + text, width="stretch")
        else:
            st.info("No macro data available")

    with divider_col:
        st.markdown("<div style='border-left: 2px solid #444; height: 400px; margin: 0 auto;'></div>", unsafe_allow_html=True)

    with chart_col2:
        st.subheader("Weight Trend")
        if has_weight:
            weight_data = df_daily.filter(pl.col("weight_kg").is_not_null())

            # Weight metrics
            w1, w2, w3 = st.columns(3)
            with w1:
                latest_weight = weight_data.sort("date", descending=True)["weight_kg"].head(1).item()
                metric_with_goal("Current", latest_weight, unit=" kg", fmt=".1f")
            with w2:
                avg_weight = weight_data["weight_kg"].mean()
                metric_with_goal("Average", avg_weight, unit=" kg", fmt=".1f")
            with w3:
                min_weight = weight_data["weight_kg"].min()
                max_weight = weight_data["weight_kg"].max()
                st.metric("Range", f"{min_weight:.1f} - {max_weight:.1f} kg")

            # Weight chart with average line
            if weight_data.height > 1:
                weight_chart_data = (
                    weight_data
                    .with_columns(pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("Date"))
                    .select(["Date", "weight_kg"])
                    .to_pandas()
                )

                # Main line chart
                chart = alt.Chart(weight_chart_data).mark_line(point=True).encode(
                    x=alt.X("Date:N", sort=None, title="Date"),
                    y=alt.Y("weight_kg:Q", title="Weight (kg)", scale=alt.Scale(zero=False)),
                )

                # Data point labels
                text = alt.Chart(weight_chart_data).mark_text(dy=-10, fontSize=11).encode(
                    x=alt.X("Date:N", sort=None),
                    y=alt.Y("weight_kg:Q"),
                    text=alt.Text("weight_kg:Q", format=".1f")
                )

                # Average line
                avg_weight_val = round(weight_chart_data["weight_kg"].mean(), 2)
                avg_line = alt.Chart(weight_chart_data).mark_rule(
                    color="#ff6b6b",
                    strokeDash=[5, 5],
                    strokeWidth=2
                ).encode(
                    y=alt.datum(avg_weight_val)
                )

                st.altair_chart(chart + text + avg_line, width="stretch")
        else:
            st.info("No weight data available")

    st.divider()

    # Detailed Breakdown - two tables side by side
    st.subheader("Detailed Breakdown")

    table_col1, table_col2 = st.columns(2)

    with table_col1:
        st.markdown("**Daily Nutrition**")
        # Only show nutrition data when macros are logged (not Apple Watch calories)
        if has_macros:
            nutrition_cols = ["date", "protein_g", "carbs_g", "fat_g", "logged_calories"]
            table_data = df_daily.filter(pl.col("protein_g").is_not_null())

            if table_data.height > 0:
                display_table = (
                    table_data
                    .with_columns(pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("date"))
                    .select([c for c in nutrition_cols if c in table_data.columns])
                    .sort("date", descending=True)
                )
                st.dataframe(
                    display_table.to_pandas(),
                    column_config={
                        "date": st.column_config.TextColumn("Date", width="small"),
                        "protein_g": st.column_config.NumberColumn("Protein (g)", format="%.0f", width="small"),
                        "carbs_g": st.column_config.NumberColumn("Carbs (g)", format="%.0f", width="small"),
                        "fat_g": st.column_config.NumberColumn("Fat (g)", format="%.0f", width="small"),
                        "logged_calories": st.column_config.NumberColumn("Calories", format="%.0f", width="small"),
                    },
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.info("No nutrition data for selected period")
        else:
            st.info("No nutrition data available")

    with table_col2:
        st.markdown("**Daily Weight**")
        if has_weight:
            weight_table = (
                df_daily
                .filter(pl.col("weight_kg").is_not_null())
                .with_columns(pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("date"))
                .select(["date", "weight_kg"])
                .sort("date", descending=True)
            )
            if weight_table.height > 0:
                st.dataframe(
                    weight_table.to_pandas(),
                    column_config={
                        "date": st.column_config.TextColumn("Date", width="small"),
                        "weight_kg": st.column_config.NumberColumn("Weight (kg)", format="%.1f", width="small"),
                    },
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.info("No weight data for selected period")
        else:
            st.info("No weight data available")
else:
    st.info("No calorie or macro data available - log food in an app that syncs to Apple Health")

# Footer
st.divider()
st.caption("*All metric values shown are averages for the selected date range.*")
