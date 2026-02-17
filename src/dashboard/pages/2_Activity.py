"""Activity page — Steps & movement."""

from datetime import timedelta

import altair as alt
import polars as pl
import streamlit as st

st.set_page_config(page_title="🚶 Activity", page_icon="🚶", layout="wide")

from dashboard.components import date_filter_sidebar, metric_with_goal  # noqa: E402
from dashboard.config import GOALS  # noqa: E402
from dashboard.data import load_parquet  # noqa: E402


@st.cache_data(ttl=timedelta(hours=1), show_spinner="Loading health data...")
def load_daily_summary() -> pl.DataFrame:
    """Load recent daily summary table (last 90 days, cached across reruns)."""
    return load_parquet("fct_daily_summary_recent")


# Sidebar - Date Filter
start_date, end_date = date_filter_sidebar(
    presets=["Last 7 days", "Last 30 days", "Last 90 days", "This month", "Custom"],
    max_lookback=90,
)

# Load data
df_all = load_daily_summary()
if df_all.height > 0 and "date" in df_all.columns:
    df_daily = df_all.filter(
        (pl.col("date") >= pl.lit(start_date)) & (pl.col("date") <= pl.lit(end_date))
    )
else:
    df_daily = df_all

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
    st.caption(
        f":green-background[At goal]  :blue-background[Below goal]  "
        f":red[--- {GOALS['steps']:,.0f} steps goal]"
    )
    if steps_data.height > 0:
        steps_chart_data = (
            steps_data.with_columns(
                [
                    pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("Date"),
                    pl.col("steps").round(0).cast(pl.Int64).alias("steps"),
                ]
            )
            .select(["Date", "steps"])
            .to_pandas()
        )

        bars = (
            alt.Chart(steps_chart_data)
            .mark_bar()
            .encode(
                x=alt.X("Date:N", sort=None, title="Date"),
                y=alt.Y("steps:Q", title="Steps"),
                color=alt.condition(
                    alt.datum.steps >= GOALS["steps"],
                    alt.value("#00CC96"),
                    alt.value("#636EFA"),
                ),
            )
        )

        # Goal line
        goal_line = (
            alt.Chart(steps_chart_data)
            .mark_rule(color="#ff6b6b", strokeDash=[5, 5], strokeWidth=2)
            .encode(y=alt.datum(GOALS["steps"]))
        )

        # Labels on top of bars
        text = (
            alt.Chart(steps_chart_data)
            .mark_text(dy=-10, fontSize=11, fontWeight="bold", color="white")
            .encode(
                x=alt.X("Date:N", sort=None),
                y=alt.Y("steps:Q"),
                text=alt.Text("steps:Q", format=",.0f"),
            )
        )

        st.altair_chart(bars + goal_line + text, width="stretch")
else:
    st.info("No step data available for selected period")

# Footer
st.divider()
st.caption("*All metric values shown are averages for the selected date range.*")
