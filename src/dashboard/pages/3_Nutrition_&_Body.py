"""Nutrition & Body page — Macros, Calories, and Weight."""

from datetime import timedelta

import altair as alt
import polars as pl
import streamlit as st

st.set_page_config(page_title="🍽️ Nutrition & Body", page_icon="🍽️", layout="wide")

from dashboard.components import metric_with_goal  # noqa: E402
from dashboard.config import GOALS, today_local  # noqa: E402
from dashboard.data import load_parquet  # noqa: E402


@st.cache_data(ttl=timedelta(hours=1), show_spinner="Loading health data...")
def load_daily_summary() -> pl.DataFrame:
    """Load recent daily summary table (last 90 days, cached across reruns)."""
    return load_parquet("fct_daily_summary_recent")


df_all = load_daily_summary()

# =============================================================================
# Calories & Macros Section
# =============================================================================
st.header("Calories & Macros")

has_macros = "protein_g" in df_all.columns and df_all["protein_g"].drop_nulls().len() > 0
has_weight = "weight_kg" in df_all.columns and df_all["weight_kg"].drop_nulls().len() > 0

if has_macros or has_weight:
    # Period selector for this page
    section_days = st.selectbox(
        "Period",
        [7, 14, 30, 60, 90],
        index=0,
        format_func=lambda d: f"Last {d} days",
        key="macros_weight_period",
    )
    section_cutoff = today_local() - timedelta(days=section_days)
    section_data = (
        df_all.filter(pl.col("date") >= pl.lit(section_cutoff)) if df_all.height > 0 else df_all
    )
    macro_data = (
        section_data.filter(pl.col("protein_g").is_not_null()) if has_macros else pl.DataFrame()
    )

    # Metrics row: Protein, Carbs, Fat, Calories (from macros)
    if has_macros and macro_data.height > 0:
        avg_protein = float(macro_data["protein_g"].mean())
        avg_carbs = float(macro_data["carbs_g"].mean())
        avg_fat = float(macro_data["fat_g"].mean())
        avg_calories = round(avg_protein * 4 + avg_carbs * 4 + avg_fat * 9)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_with_goal("Protein", avg_protein, GOALS["protein_g"], "g", ".0f")
        with c2:
            metric_with_goal("Carbs", avg_carbs, GOALS["carbs_g"], "g", ".0f")
        with c3:
            metric_with_goal("Fat", avg_fat, GOALS["fat_g"], "g", ".0f")
        with c4:
            st.metric("Calories", f"{avg_calories:,}")

    chart_left, chart_right = st.columns(2)

    # --- Daily Macros (left) ---
    with chart_left:
        st.subheader("Daily Macros (g)")
        if has_macros and macro_data.height > 0:
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

            bars = (
                alt.Chart(macro_melted)
                .mark_bar()
                .encode(
                    x=alt.X("Date:N", sort=None, title="Date"),
                    y=alt.Y("Grams:Q", title="Grams"),
                    color=alt.Color(
                        "Macro:N",
                        scale=alt.Scale(
                            domain=["Protein", "Carbs", "Fat"],
                            range=["#00CC96", "#FFA15A", "#EF553B"],
                        ),
                    ),
                    order=alt.Order("Macro:N", sort="descending"),
                )
            )

            totals = macro_chart_data[["Date", "total_macros"]].drop_duplicates()
            text = (
                alt.Chart(totals)
                .mark_text(dy=-10, fontSize=12, fontWeight="bold", color="white")
                .encode(
                    x=alt.X("Date:N", sort=None),
                    y=alt.Y("total_macros:Q"),
                    text=alt.Text("total_macros:Q", format=".0f"),
                )
            )

            st.altair_chart(bars + text, width="stretch")
        else:
            st.info("No macro data available for selected period")

    # --- Weight Trend (right) ---
    with chart_right:
        st.subheader("Weight Trend")
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
                    st.metric("Range", f"{min_weight:.1f} - {max_weight:.1f} kg")

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

                text = (
                    alt.Chart(weight_chart_data)
                    .mark_text(dy=-10, fontSize=11, color="white")
                    .encode(
                        x=alt.X("Date:N", sort=None),
                        y=alt.Y("weight_kg:Q"),
                        text=alt.Text("weight_kg:Q", format=".1f"),
                    )
                )

                avg_line = (
                    alt.Chart(weight_chart_data)
                    .mark_rule(
                        color="#ff6b6b",
                        strokeDash=[5, 5],
                        strokeWidth=2,
                    )
                    .encode(y=alt.datum(round(avg_weight, 2)))
                )

                st.altair_chart(line + text + avg_line, width="stretch")
            else:
                st.info("No weight data for selected period")
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
            table_data = section_data.filter(pl.col("protein_g").is_not_null())

            if table_data.height > 0:
                display_table = (
                    table_data.with_columns(
                        pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("date")
                    )
                    .select([c for c in nutrition_cols if c in table_data.columns])
                    .sort("date", descending=True)
                )
                st.dataframe(
                    display_table.to_pandas(),
                    column_config={
                        "date": st.column_config.TextColumn("Date", width="small"),
                        "protein_g": st.column_config.NumberColumn(
                            "Protein (g)", format="%.0f", width="small"
                        ),
                        "carbs_g": st.column_config.NumberColumn(
                            "Carbs (g)", format="%.0f", width="small"
                        ),
                        "fat_g": st.column_config.NumberColumn(
                            "Fat (g)", format="%.0f", width="small"
                        ),
                        "logged_calories": st.column_config.NumberColumn(
                            "Calories", format="%.0f", width="small"
                        ),
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
                section_data.filter(pl.col("weight_kg").is_not_null())
                .with_columns(pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("date"))
                .select(["date", "weight_kg"])
                .sort("date", descending=True)
            )
            if weight_table.height > 0:
                st.dataframe(
                    weight_table.to_pandas(),
                    column_config={
                        "date": st.column_config.TextColumn("Date", width="small"),
                        "weight_kg": st.column_config.NumberColumn(
                            "Weight (kg)", format="%.1f", width="small"
                        ),
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
st.caption("*All metric values shown are averages for the selected period.*")
