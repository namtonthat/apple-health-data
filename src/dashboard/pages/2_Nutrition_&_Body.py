"""Nutrition & Body page — Macros, Calories, and Weight."""

import altair as alt
import pandas as pd
import polars as pl
import streamlit as st

st.set_page_config(page_title="🍽️ Nutrition & Body", page_icon="🍽️", layout="wide")

from dashboard.components import (  # noqa: E402
    date_filter_sidebar,
    goal_status_color,
    metric_with_goal_color,
)
from dashboard.config import GOALS  # noqa: E402
from dashboard.data import load_daily_summary, load_weight_rolling_averages  # noqa: E402

# Sidebar - Date Filter
start_date, end_date = date_filter_sidebar(
    presets=["Last 7 days", "Last 14 days", "Last 30 days", "Last 90 days", "This month", "Custom"],
    max_lookback=90,
)

df_all = load_daily_summary()

has_macros = "protein_g" in df_all.columns and df_all["protein_g"].drop_nulls().len() > 0
has_weight = "weight_kg" in df_all.columns and df_all["weight_kg"].drop_nulls().len() > 0

if has_macros or has_weight:
    section_data = (
        df_all.filter((pl.col("date") >= pl.lit(start_date)) & (pl.col("date") <= pl.lit(end_date)))
        if df_all.height > 0
        else df_all
    )
    macro_data = (
        section_data.filter(pl.col("protein_g").is_not_null()) if has_macros else pl.DataFrame()
    )

    # Show data availability for the period
    if has_macros and macro_data.height > 0:
        latest_macro_date = macro_data.sort("date", descending=True)["date"].head(1).item()
        days_in_range = section_data.height
        days_with_macros = macro_data.height
        if days_with_macros < days_in_range:
            st.caption(
                f"*Nutrition logged for {days_with_macros} of {days_in_range} days "
                f"(latest: {latest_macro_date})*"
            )
    elif has_macros:
        st.info("No nutrition data logged for the selected period.")

    # =============================================================================
    # Two-column layout: Macros (left) | Weight (right)
    # =============================================================================
    col_macros, col_weight = st.columns(2)

    # -------------------------------------------------------------------------
    # LEFT COLUMN — Macros & Calories
    # -------------------------------------------------------------------------
    with col_macros:
        st.header("Calories & Macros")

        if has_macros and macro_data.height > 0:
            avg_protein = float(macro_data["protein_g"].mean())
            avg_carbs = float(macro_data["carbs_g"].mean())
            avg_fat = float(macro_data["fat_g"].mean())
            avg_calories = round(avg_protein * 4 + avg_carbs * 4 + avg_fat * 9)

            m1, m2 = st.columns(2)
            with m1:
                metric_with_goal_color("Protein", avg_protein, GOALS["protein_g"], "g", ".0f")
                metric_with_goal_color("Carbs", avg_carbs, GOALS["carbs_g"], "g", ".0f")
            with m2:
                metric_with_goal_color("Fat", avg_fat, GOALS["fat_g"], "g", ".0f")
                metric_with_goal_color("Calories", avg_calories, GOALS["calories"], "", ",.0f")

            # --- Daily Macros Chart ---
            st.subheader("Daily Macros (g)")
            macro_chart_data = (
                macro_data.with_columns(
                    [
                        pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("Date"),
                        (pl.col("protein_g") + pl.col("carbs_g") + pl.col("fat_g")).alias(
                            "total_macros"
                        ),
                    ]
                )
                .select(["Date", "protein_g", "carbs_g", "fat_g", "total_macros"])
                .to_pandas()
            )

            macro_melted = macro_chart_data.melt(
                id_vars=["Date", "total_macros"],
                value_vars=["protein_g", "carbs_g", "fat_g"],
                var_name="Macro",
                value_name="Grams",
            )
            macro_melted["Macro"] = macro_melted["Macro"].map(
                {
                    "protein_g": "Protein",
                    "carbs_g": "Carbs",
                    "fat_g": "Fat",
                }
            )

            macro_order = ["Protein", "Carbs", "Fat"]
            color_scale = alt.Scale(
                domain=macro_order,
                range=["#00CC96", "#FFA15A", "#EF553B"],
            )

            bars = (
                alt.Chart(macro_melted)
                .mark_bar()
                .encode(
                    x=alt.X("Date:N", sort=None, title="Date"),
                    y=alt.Y("Grams:Q", title="Grams"),
                    color=alt.Color("Macro:N", scale=color_scale),
                    order=alt.Order("Macro:N", sort="descending"),
                )
            )

            totals = macro_chart_data.copy()
            totals["label"] = totals.apply(
                lambda r: f"{int(r['protein_g'])}P {int(r['carbs_g'])}C {int(r['fat_g'])}F",
                axis=1,
            )

            text = (
                alt.Chart(totals)
                .mark_text(dy=-10, fontSize=11, fontWeight="bold", color="white")
                .encode(
                    x=alt.X("Date:N", sort=None),
                    y=alt.Y("total_macros:Q"),
                    text=alt.Text("label:N"),
                )
            )

            st.altair_chart(bars + text, use_container_width=True)

            # --- Daily Nutrition Table ---
            st.subheader("Daily Nutrition")
            nutrition_cols = ["date", "protein_g", "carbs_g", "fat_g", "logged_calories"]
            table_data = section_data.filter(pl.col("protein_g").is_not_null())

            if table_data.height > 0:
                display_table = (
                    table_data.with_columns(
                        pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("date")
                    )
                    .select([c for c in nutrition_cols if c in table_data.columns])
                    .sort("date", descending=True)
                )

                display_df = display_table.to_pandas()
                display_df.columns = ["Date", "Protein (g)", "Carbs (g)", "Fat (g)", "Calories"]

                macro_goals = {
                    "Protein (g)": GOALS["protein_g"],
                    "Carbs (g)": GOALS["carbs_g"],
                    "Fat (g)": GOALS["fat_g"],
                    "Calories": GOALS["calories"],
                }

                def _style_macro(val, goal):
                    if pd.isna(val):
                        return ""
                    color = goal_status_color(float(val), goal)
                    return f"background-color: {color}33; color: {color}"

                styled = display_df.style.apply(
                    lambda col: [
                        _style_macro(v, macro_goals[col.name]) if col.name in macro_goals else ""
                        for v in col
                    ],
                    axis=0,
                ).format(
                    {
                        "Protein (g)": "{:.0f}",
                        "Carbs (g)": "{:.0f}",
                        "Fat (g)": "{:.0f}",
                        "Calories": "{:.0f}",
                    }
                )

                st.dataframe(styled, hide_index=True, use_container_width=True)
            else:
                st.info("No nutrition data for selected period")
        else:
            st.info("No macro data available for selected period")

    # -------------------------------------------------------------------------
    # RIGHT COLUMN — Weight & Body
    # -------------------------------------------------------------------------
    with col_weight:
        st.header("Weight & Body")

        if has_weight:
            weight_data = section_data.filter(pl.col("weight_kg").is_not_null())
            if weight_data.height > 0:
                latest_weight = float(
                    weight_data.sort("date", descending=True)["weight_kg"].head(1).item()
                )
                avg_weight = float(weight_data["weight_kg"].mean())
                min_weight = float(weight_data["weight_kg"].min())
                max_weight = float(weight_data["weight_kg"].max())

                w1, w2, w3 = st.columns(3)
                with w1:
                    st.metric("Current", f"{latest_weight:.1f} kg")
                with w2:
                    st.metric("Average", f"{avg_weight:.1f} kg")
                with w3:
                    st.metric("Range", f"{min_weight:.1f} – {max_weight:.1f} kg")

                # --- Weight Trend Chart ---
                st.subheader("Weight Trend")
                weight_chart_data = (
                    weight_data.with_columns(
                        pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("Date")
                    )
                    .select(["Date", "weight_kg"])
                    .to_pandas()
                )

                line = (
                    alt.Chart(weight_chart_data)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("Date:N", sort=None, title="Date"),
                        y=alt.Y("weight_kg:Q", title="Weight (kg)", scale=alt.Scale(zero=False)),
                    )
                )

                wt_text = (
                    alt.Chart(weight_chart_data)
                    .mark_text(dy=-10, fontSize=11, color="white")
                    .encode(
                        x=alt.X("Date:N", sort=None),
                        y=alt.Y("weight_kg:Q"),
                        text=alt.Text("weight_kg:Q", format=".1f"),
                    )
                )

                goal_line = (
                    alt.Chart(weight_chart_data)
                    .mark_rule(color="#00CC96", strokeDash=[5, 5], strokeWidth=2)
                    .encode(y=alt.datum(GOALS["weight_kg"]))
                )

                avg_line = (
                    alt.Chart(weight_chart_data)
                    .mark_rule(color="#ff6b6b", strokeDash=[5, 5], strokeWidth=2)
                    .encode(y=alt.datum(round(avg_weight, 2)))
                )

                st.altair_chart(line + wt_text + goal_line + avg_line, use_container_width=True)
                st.caption(
                    f":green[--- {GOALS['weight_kg']:.0f} kg goal]  "
                    f":red[--- {avg_weight:.1f} kg avg]"
                )

                # --- Rolling Averages Table ---
                st.subheader("Rolling Averages")
                df_weight_avg = load_weight_rolling_averages()
                if df_weight_avg.height > 0:
                    weight_goal = GOALS["weight_kg"]
                    latest_avg = df_weight_avg.sort("date", descending=True).head(1)

                    labels = ["Now", "7d", "14d", "30d", "60d", "120d"]
                    src_cols = [
                        "weight_kg",
                        "avg_7d",
                        "avg_14d",
                        "avg_30d",
                        "avg_60d",
                        "avg_120d",
                    ]

                    values = []
                    deltas = []
                    for c in src_cols:
                        val = latest_avg[c].item()
                        if val is not None:
                            val = float(val)
                            values.append(f"{val:.1f}")
                            deltas.append(f"{val - weight_goal:+.1f}")
                        else:
                            values.append("—")
                            deltas.append("—")

                    table_df = pd.DataFrame({"Window": labels, "kg": values, "vs Goal": deltas})

                    def _weight_goal_style(row):
                        styles = [""] * len(row)
                        for i, col_name in enumerate(row.index):
                            if col_name == "vs Goal" and row[col_name] != "—":
                                diff = float(row[col_name])
                                if abs(diff) <= weight_goal * 0.02:
                                    color = "#00CC96"
                                elif abs(diff) <= weight_goal * 0.05:
                                    color = "#FFA500"
                                else:
                                    color = "#EF553B"
                                styles[i] = f"background-color: {color}33; color: {color}"
                        return styles

                    styled_wt = table_df.style.apply(_weight_goal_style, axis=1).hide(axis="index")
                    st.dataframe(styled_wt, hide_index=True, use_container_width=True)

                    st.caption(
                        f"*Goal: **{weight_goal:.0f} kg** · "
                        "**Now**: latest weigh-in · "
                        "**7d–120d**: rolling avg · "
                        "**vs Goal**: diff from target "
                        "(green ≤2%, orange ≤5%, red >5%)*"
                    )

                # --- Daily Weight Table ---
                st.subheader("Daily Weight")
                weight_table = (
                    weight_data.with_columns(
                        pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("date")
                    )
                    .select(["date", "weight_kg"])
                    .sort("date", descending=True)
                )
                st.dataframe(
                    weight_table,
                    column_config={
                        "date": st.column_config.TextColumn("Date", width="small"),
                        "weight_kg": st.column_config.NumberColumn(
                            "Weight (kg)", format="%.1f", width="small"
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("No weight data for selected period")
        else:
            st.info("No weight data available")
else:
    st.info("No calorie or macro data available - log food in an app that syncs to Apple Health")

# Footer
st.divider()
st.caption("*All metric values shown are averages for the selected period.*")
