"""Recovery & Health page."""

import os
from datetime import date, timedelta
from pathlib import Path

import altair as alt
import duckdb
import polars as pl
import streamlit as st

st.set_page_config(page_title="Recovery & Health", page_icon="😴", layout="wide")

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

# S3 configuration
S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "")
S3_TRANSFORMED_PREFIX = "transformed"


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


def load_daily_summary(start_date: date, end_date: date) -> pl.DataFrame:
    conn = get_connection()
    s3_path = get_s3_path("fct_daily_summary")
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

# =============================================================================
# Sleep Section
# =============================================================================
st.header("Sleep")

if "sleep_hours" in df_daily.columns and df_daily["sleep_hours"].drop_nulls().len() > 0:
    sleep_data = df_daily.filter(pl.col("sleep_hours").is_not_null())

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

        st.altair_chart(bars + text, use_container_width=True)
else:
    st.info("No sleep data available for selected period")

st.divider()

# =============================================================================
# Calories & Macros Section
# =============================================================================
st.header("Calories & Macros")

# Check if we have calorie/macro data
has_calories = "total_calories" in df_daily.columns and df_daily["total_calories"].drop_nulls().len() > 0
has_macros = "protein_g" in df_daily.columns and df_daily["protein_g"].drop_nulls().len() > 0

if has_calories or has_macros:
    # Summary metrics row
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Calories Burned")
        if has_calories:
            cal_data = df_daily.filter(pl.col("total_calories").is_not_null())
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
        else:
            st.info("No calorie data available")

    with col2:
        st.subheader("Macros (Avg)")
        if has_macros:
            macro_data = df_daily.filter(pl.col("protein_g").is_not_null())
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
        else:
            st.info("No macro data available")

    # Macros bar chart with labels
    if has_macros:
        st.subheader("Daily Macros (g)")
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

            # Melt for stacked bar chart
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

            # Stacked bar chart
            bars = alt.Chart(macro_melted).mark_bar().encode(
                x=alt.X("Date:N", sort=None, title="Date"),
                y=alt.Y("Grams:Q", title="Grams"),
                color=alt.Color("Macro:N", scale=alt.Scale(
                    domain=["Protein", "Carbs", "Fat"],
                    range=["#00CC96", "#FFA15A", "#EF553B"]
                )),
                order=alt.Order("Macro:N", sort="descending")
            )

            # Total label on top of each bar
            totals = macro_chart_data[["Date", "total_macros"]].drop_duplicates()
            text = alt.Chart(totals).mark_text(dy=-10, fontSize=12, fontWeight="bold").encode(
                x=alt.X("Date:N", sort=None),
                y=alt.Y("total_macros:Q"),
                text=alt.Text("total_macros:Q", format=".0f")
            )

            st.altair_chart(bars + text, use_container_width=True)

    # Daily nutrition table
    st.subheader("Daily Nutrition Table")
    nutrition_cols = ["date"]
    if has_macros:
        nutrition_cols.extend(["protein_g", "carbs_g", "fat_g"])
    if has_calories:
        nutrition_cols.append("total_calories")

    # Filter to only rows with data
    table_data = df_daily
    if has_macros:
        table_data = table_data.filter(pl.col("protein_g").is_not_null() | pl.col("total_calories").is_not_null())
    elif has_calories:
        table_data = table_data.filter(pl.col("total_calories").is_not_null())

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
                "total_calories": st.column_config.NumberColumn("Total Calories", format="%.0f", width="small"),
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No nutrition data for selected period")
else:
    st.info("No calorie or macro data available - log food in an app that syncs to Apple Health")
