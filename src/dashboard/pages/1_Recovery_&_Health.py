"""Recovery & Health page."""

from datetime import date, timedelta

import altair as alt
import polars as pl
import streamlit as st

st.set_page_config(page_title="😴 Recovery & Health", page_icon="😴", layout="wide")

from dashboard.components import date_filter_sidebar, metric_with_goal, vertical_divider
from dashboard.config import GOALS
from dashboard.data import load_parquet


@st.cache_data(ttl=timedelta(hours=1), show_spinner="Loading health data...")
def load_recent_summary() -> pl.DataFrame:
    """Load the full 90-day recent table (cached across reruns)."""
    return load_parquet("fct_daily_summary_recent")


# Sidebar - Date Filter
start_date, end_date = date_filter_sidebar(
    presets=["Last 7 days", "Last 30 days", "Last 90 days", "This month", "Custom"],
    max_lookback=90,
)

# Load data — use cached table for presets, fresh query for custom
df_all = load_recent_summary()
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
        metric_with_goal("Deep", sleep_data["sleep_deep_hours"].mean(), GOALS["sleep_deep_hours"], "h")
    with col3:
        metric_with_goal("REM", sleep_data["sleep_rem_hours"].mean(), GOALS["sleep_rem_hours"], "h")
    with col4:
        metric_with_goal("Light", sleep_data["sleep_light_hours"].mean(), GOALS["sleep_light_hours"], "h")
    with col5:
        days_hit = sleep_data.filter(pl.col("sleep_hours") >= GOALS["sleep_hours"]).height
        total_days = sleep_data.height
        st.metric("Days at Goal", f"{days_hit} / {total_days}")

    # Sleep charts — stages (grouped) and total side by side
    if sleep_data.height > 0:
        sleep_chart_data = (
            sleep_data
            .with_columns(pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("Date"))
            .select(["Date", "sleep_deep_hours", "sleep_rem_hours", "sleep_light_hours", "sleep_hours"])
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
            sleep_melted["Stage"] = sleep_melted["Stage"].map({
                "sleep_deep_hours": "Deep",
                "sleep_rem_hours": "REM",
                "sleep_light_hours": "Light",
            })

            # Grouped (side-by-side) bar chart with labels
            base = alt.Chart(sleep_melted).encode(
                x=alt.X("Date:N", sort=None, title="Date"),
                y=alt.Y("Hours:Q", title="Hours"),
                color=alt.Color("Stage:N", scale=alt.Scale(
                    domain=["Deep", "REM", "Light"],
                    range=["#1f77b4", "#9467bd", "#ff7f0e"],
                )),
                xOffset="Stage:N",
            )

            bars = base.mark_bar()
            text = base.mark_text(dy=-8, fontSize=10).encode(
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
            total_bars = alt.Chart(sleep_chart_data).mark_bar().encode(
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

            # 6h warning line (red)
            warn_line = alt.Chart(sleep_chart_data).mark_rule(
                color="#EF553B", strokeDash=[5, 5], strokeWidth=2,
            ).encode(y=alt.datum(6))

            # 7h goal line (green)
            goal_line = alt.Chart(sleep_chart_data).mark_rule(
                color="#00CC96", strokeDash=[5, 5], strokeWidth=2,
            ).encode(y=alt.datum(sleep_goal))

            # Labels
            text = alt.Chart(sleep_chart_data).mark_text(
                dy=-10, fontSize=12, fontWeight="bold", color="white",
            ).encode(
                x=alt.X("Date:N", sort=None),
                y=alt.Y("Hours asleep:Q"),
                text=alt.Text("Hours asleep:Q", format=".1f"),
            )

            st.altair_chart(
                total_bars + warn_line + goal_line + text,
                width="stretch",
            )
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
            .with_columns([
                pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("Date"),
                pl.col("steps").round(0).cast(pl.Int64).alias("steps"),
            ])
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
    cal_col, divider_col, macro_col = st.columns([1, 0.05, 1])

    with cal_col:
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

    with divider_col:
        vertical_divider(120)

    with macro_col:
        st.subheader("Macros")
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
        vertical_divider(400)

    with chart_col2:
        st.subheader("Weight Trend")
        if has_weight:
            weight_data = df_daily.filter(pl.col("weight_kg").is_not_null())

            # Weight metrics — current & average vs Nd avg, range
            all_wt = df_all.filter(pl.col("weight_kg").is_not_null()) if (df_all.height > 0 and "weight_kg" in df_all.columns) else weight_data
            latest_weight = float(weight_data.sort("date", descending=True)["weight_kg"].head(1).item())

            compare_days = st.selectbox(
                "Compare against", [7, 14, 30, 60, 90],
                index=2, format_func=lambda d: f"Last {d} days",
                key="weight_compare",
            )
            compare_date = date.today() - timedelta(days=compare_days)
            compare_data = all_wt.filter(pl.col("date") >= pl.lit(compare_date))
            ref_avg = float(compare_data["weight_kg"].mean()) if compare_data.height > 0 else None
            ref_label = f"{compare_days}d avg"

            w1, w2, w3 = st.columns(3)
            with w1:
                metric_with_goal("Current", latest_weight, ref_avg, " kg", ".1f", inverse=True, ref_label=ref_label)
            with w2:
                avg_weight = float(weight_data["weight_kg"].mean())
                metric_with_goal("Average", avg_weight, ref_avg, " kg", ".1f", inverse=True, ref_label=ref_label)
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
