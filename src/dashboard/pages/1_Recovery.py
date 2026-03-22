"""Recovery page — Sleep, Meditation & Steps."""

import altair as alt
import pandas as pd
import polars as pl
import streamlit as st

st.set_page_config(page_title="😴 Recovery", page_icon="😴", layout="wide")

from dashboard.components import (  # noqa: E402
    date_filter_sidebar,
    goal_status_color,
    metric_with_goal,
)
from dashboard.config import GOALS  # noqa: E402
from dashboard.data import load_daily_summary, load_daily_workouts  # noqa: E402

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
        metric_with_goal(
            "Deep", sleep_data["sleep_deep_hours"].mean(), GOALS["sleep_deep_hours"], "h"
        )
    with col3:
        metric_with_goal("REM", sleep_data["sleep_rem_hours"].mean(), GOALS["sleep_rem_hours"], "h")
    with col4:
        metric_with_goal(
            "Light", sleep_data["sleep_light_hours"].mean(), GOALS["sleep_light_hours"], "h"
        )
    with col5:
        days_hit = sleep_data.filter(pl.col("sleep_hours") >= GOALS["sleep_hours"]).height
        total_days = sleep_data.height
        st.metric("Days at Goal", f"{days_hit} / {total_days}")

    # Sleep charts — stages (grouped) and total side by side
    if sleep_data.height > 0:
        sleep_chart_data = (
            sleep_data.with_columns(
                pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("Date")
            )
            .select(
                ["Date", "sleep_deep_hours", "sleep_rem_hours", "sleep_light_hours", "sleep_hours"]
            )
            .to_pandas()
            .rename(columns={"sleep_hours": "Hours asleep"})
        )

        chart_left, chart_right = st.columns(2)

        with chart_left:
            st.subheader("Sleep Stages")
            # Melt for grouped bar chart
            sleep_melted = sleep_chart_data.melt(
                id_vars=["Date"],
                value_vars=["sleep_deep_hours", "sleep_rem_hours", "sleep_light_hours"],
                var_name="Stage",
                value_name="Hours",
            )
            sleep_melted["Stage"] = sleep_melted["Stage"].map(
                {
                    "sleep_deep_hours": "Deep",
                    "sleep_rem_hours": "REM",
                    "sleep_light_hours": "Light",
                }
            )

            # Grouped (side-by-side) bar chart with labels
            base = alt.Chart(sleep_melted).encode(
                x=alt.X("Date:N", sort=None, title="Date"),
                y=alt.Y("Hours:Q", title="Hours"),
                color=alt.Color(
                    "Stage:N",
                    scale=alt.Scale(
                        domain=["Deep", "REM", "Light"],
                        range=["#1f77b4", "#9467bd", "#ff7f0e"],
                    ),
                ),
                xOffset="Stage:N",
            )

            bars = base.mark_bar()
            text = base.mark_text(dy=-8, fontSize=10, color="white").encode(
                text=alt.Text("Hours:Q", format=".1f"),
            )

            st.altair_chart(bars + text, width="stretch")

        with chart_right:
            st.subheader("Total Sleep")
            st.caption(
                ":red-background[< 6h]  :orange-background[6 - 7h]  :green-background[7+ hours]  \n"
                ":red[--- 6 hours]  :green[--- 7 hours]"
            )
            # Bar chart — 3 tiers: <6 red, 6-7 orange, 7+ green
            sleep_goal = GOALS["sleep_hours"]
            total_bars = (
                alt.Chart(sleep_chart_data)
                .mark_bar()
                .encode(
                    x=alt.X("Date:N", sort=None, title="Date"),
                    y=alt.Y("Hours asleep:Q", title=None),
                    color=alt.Color(
                        "Hours asleep:Q",
                        scale=alt.Scale(
                            domain=[6, sleep_goal],
                            range=["#EF553B", "#FFA15A", "#00CC96"],
                            type="threshold",
                        ),
                        legend=None,
                    ),
                    tooltip=alt.value(None),
                )
            )

            # 6h warning line (red)
            warn_line = (
                alt.Chart(sleep_chart_data)
                .mark_rule(
                    color="#EF553B",
                    strokeDash=[5, 5],
                    strokeWidth=2,
                )
                .encode(y=alt.datum(6))
            )

            # 7h goal line (green)
            goal_line = (
                alt.Chart(sleep_chart_data)
                .mark_rule(
                    color="#00CC96",
                    strokeDash=[5, 5],
                    strokeWidth=2,
                )
                .encode(y=alt.datum(sleep_goal))
            )

            # Labels
            text = (
                alt.Chart(sleep_chart_data)
                .mark_text(
                    dy=-10,
                    fontSize=12,
                    fontWeight="bold",
                    color="white",
                )
                .encode(
                    x=alt.X("Date:N", sort=None),
                    y=alt.Y("Hours asleep:Q"),
                    text=alt.Text("Hours asleep:Q", format=".1f"),
                )
            )

            st.altair_chart(
                total_bars + warn_line + goal_line + text,
                width="stretch",
            )
else:
    st.info("No sleep data available for selected period")

st.divider()

# =============================================================================
# Meditation Section
# =============================================================================
st.header("Meditation")

has_meditation = (
    "meditation_minutes" in df_daily.columns
    and df_daily["meditation_minutes"].drop_nulls().len() > 0
)

if has_meditation:
    med_data = df_daily.filter(pl.col("meditation_minutes").is_not_null())

    # Metric cards
    col1, col2, col3 = st.columns(3)
    with col1:
        metric_with_goal(
            "Daily Avg",
            med_data["meditation_minutes"].mean(),
            GOALS.get("meditation_minutes"),
            "min",
            ".0f",
        )
    with col2:
        metric_with_goal("Best Day", med_data["meditation_minutes"].max(), unit="min", fmt=".0f")
    with col3:
        goal = GOALS.get("meditation_minutes")
        if goal:
            days_hit = med_data.filter(pl.col("meditation_minutes") >= goal).height
            total_days = med_data.height
            st.metric("Days at Goal", f"{days_hit} / {total_days}")
        else:
            st.metric("Total Days", f"{med_data.height}")

    # Bar chart
    if med_data.height > 0:
        med_chart_data = (
            med_data.with_columns(
                [
                    pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("Date"),
                    pl.col("meditation_minutes").round(0).cast(pl.Int64).alias("Minutes"),
                ]
            )
            .select(["Date", "Minutes"])
            .to_pandas()
        )

        goal = GOALS.get("meditation_minutes")
        if goal:
            st.caption(
                f":green-background[At goal]  :blue-background[Below goal]  "
                f":red[--- {goal:.0f} min goal]"
            )
            bars = (
                alt.Chart(med_chart_data)
                .mark_bar()
                .encode(
                    x=alt.X("Date:N", sort=None, title="Date"),
                    y=alt.Y("Minutes:Q", title="Minutes"),
                    color=alt.condition(
                        alt.datum.Minutes >= goal,
                        alt.value("#00CC96"),
                        alt.value("#636EFA"),
                    ),
                )
            )
            goal_line = (
                alt.Chart(med_chart_data)
                .mark_rule(color="#ff6b6b", strokeDash=[5, 5], strokeWidth=2)
                .encode(y=alt.datum(goal))
            )
        else:
            bars = (
                alt.Chart(med_chart_data)
                .mark_bar()
                .encode(
                    x=alt.X("Date:N", sort=None, title="Date"),
                    y=alt.Y("Minutes:Q", title="Minutes"),
                    color=alt.value("#636EFA"),
                )
            )
            goal_line = alt.Chart(med_chart_data).mark_point(opacity=0)

        text = (
            alt.Chart(med_chart_data)
            .mark_text(dy=-10, fontSize=11, fontWeight="bold", color="white")
            .encode(
                x=alt.X("Date:N", sort=None),
                y=alt.Y("Minutes:Q"),
                text=alt.Text("Minutes:Q", format=".0f"),
            )
        )

        st.altair_chart(bars + goal_line + text, width="stretch")
else:
    st.info("No meditation data available for selected period")

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

st.divider()

# =============================================================================
# Daily Breakdown Table
# =============================================================================
st.header("Health & Recovery — Daily Breakdown")

if df_daily.height > 0:
    # Build the base table from daily summary
    breakdown_cols = {
        "date": True,
        "sleep_hours": "sleep_hours" in df_daily.columns,
        "sleep_deep_hours": "sleep_deep_hours" in df_daily.columns,
        "sleep_rem_hours": "sleep_rem_hours" in df_daily.columns,
        "protein_g": "protein_g" in df_daily.columns,
        "logged_calories": "logged_calories" in df_daily.columns,
        "steps": "steps" in df_daily.columns,
        "resting_hr_bpm": "resting_hr_bpm" in df_daily.columns,
        "hrv_ms": "hrv_ms" in df_daily.columns,
        "weight_kg": "weight_kg" in df_daily.columns,
    }
    avail_cols = [c for c, present in breakdown_cols.items() if present]
    base = df_daily.select(avail_cols).sort("date", descending=True)

    # Load workout data and join
    df_workouts = load_daily_workouts()
    if df_workouts.height > 0:
        # Aggregate multiple workouts per day into one row
        workout_daily = (
            df_workouts.with_columns(
                pl.col("started_at").cast(pl.Datetime).dt.strftime("%H:%M").alias("gym_time"),
            )
            .group_by("workout_date")
            .agg(
                pl.col("workout_name").first().alias("workout"),
                pl.col("gym_time").first().alias("gym_time"),
                pl.col("workout_duration_minutes").sum().alias("gym_mins"),
            )
        )
        base = base.join(
            workout_daily,
            left_on="date",
            right_on="workout_date",
            how="left",
        )
    else:
        base = base.with_columns(
            pl.lit(None).alias("workout"),
            pl.lit(None).alias("gym_time"),
            pl.lit(None).cast(pl.Int64).alias("gym_mins"),
        )

    # Format date as "Mon 17"
    display = base.with_columns(
        pl.col("date").cast(pl.Date).dt.strftime("%a %d").alias("Day"),
    )

    # Select and rename for display
    col_map = {"Day": "Day"}
    if "sleep_hours" in avail_cols:
        col_map["sleep_hours"] = "Sleep"
    if "sleep_deep_hours" in avail_cols:
        col_map["sleep_deep_hours"] = "Deep"
    if "sleep_rem_hours" in avail_cols:
        col_map["sleep_rem_hours"] = "REM"
    col_map["workout"] = "Workout"
    col_map["gym_time"] = "Time"
    col_map["gym_mins"] = "Mins"
    if "protein_g" in avail_cols:
        col_map["protein_g"] = "Protein"
    if "logged_calories" in avail_cols:
        col_map["logged_calories"] = "Cals"
    if "steps" in avail_cols:
        col_map["steps"] = "Steps"
    if "resting_hr_bpm" in avail_cols:
        col_map["resting_hr_bpm"] = "RHR"
    if "hrv_ms" in avail_cols:
        col_map["hrv_ms"] = "HRV"
    if "weight_kg" in avail_cols:
        col_map["weight_kg"] = "Weight"

    src_cols = [c for c in col_map if c in display.columns]
    display_df = display.select(src_cols).to_pandas()
    display_df.columns = [col_map[c] for c in src_cols]

    # Goals for color coding
    goal_map = {}
    if "Sleep" in display_df.columns:
        goal_map["Sleep"] = GOALS.get("sleep_hours")
    if "Deep" in display_df.columns:
        goal_map["Deep"] = GOALS.get("sleep_deep_hours")
    if "REM" in display_df.columns:
        goal_map["REM"] = GOALS.get("sleep_rem_hours")
    if "Protein" in display_df.columns:
        goal_map["Protein"] = GOALS.get("protein_g")
    if "Cals" in display_df.columns:
        goal_map["Cals"] = GOALS.get("calories")
    if "Steps" in display_df.columns:
        goal_map["Steps"] = GOALS.get("steps")

    def _color_cell(val, goal):
        if pd.isna(val) or goal is None:
            return ""
        color = goal_status_color(float(val), goal)
        return f"background-color: {color}33; color: {color}"

    styled = display_df.style.apply(
        lambda col: [
            _color_cell(v, goal_map[col.name]) if col.name in goal_map else "" for v in col
        ],
        axis=0,
    ).format(
        {
            k: v
            for k, v in {
                "Sleep": "{:.1f}h",
                "Deep": "{:.1f}h",
                "REM": "{:.1f}h",
                "Protein": "{:.0f}g",
                "Cals": "{:,.0f}",
                "Steps": "{:,.0f}",
                "RHR": "{:.0f}",
                "HRV": "{:.0f}",
                "Weight": "{:.1f}",
                "Mins": "{:.0f}",
            }.items()
            if k in display_df.columns
        },
        na_rep="—",
    )

    st.dataframe(styled, hide_index=True, use_container_width=True)

    st.caption(
        "*Abbreviations — "
        "**Sleep/Deep/REM**: hours · "
        "**Workout**: session name · "
        "**Time**: gym start time · "
        "**Mins**: workout duration · "
        "**Protein**: grams · "
        "**Cals**: logged calories · "
        "**Steps**: daily count · "
        "**RHR**: resting heart rate (bpm) · "
        "**HRV**: heart rate variability (ms) · "
        "**Weight**: kg. "
        "Colors: green (within 10% of goal), orange (10–20% off), red (>20% off).*"
    )
else:
    st.info("No data available for the selected period.")

# Footer
st.divider()
st.caption("*All metric values shown are averages for the selected date range.*")
