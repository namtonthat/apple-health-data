"""
Helper functions for rendering graphs
"""

import altair as alt
import polars as pl
import streamlit as st

MACROS_BAR_HEIGHT = 400


def filter_metrics(
    df: pl.DataFrame,
    metrics: list[str],
    rename_map: dict[str, str] = dict(),
    sort: bool = True,
) -> pl.DataFrame:
    """
    Filter a Polars DataFrame for specific metric_names, optionally rename and sort.

    Args:
        df (pl.DataFrame): The input DataFrame.
        metrics (list[str]): List of metric_name values to filter for.
        rename_map (dict[str, str], optional): Mapping to rename metric_name values.
        sort (bool, optional): Whether to sort by metric_date and metric_name.

    Returns:
        pl.DataFrame: Filtered, optionally renamed and sorted DataFrame.
    """
    filtered = df.filter(pl.col("metric_name").is_in(metrics))

    if rename_map:
        filtered = filtered.with_columns(
            pl.col("metric_name").replace(rename_map).alias("metric_name")
        )

    if sort:
        filtered = filtered.sort(["metric_date", "metric_name"])

    return filtered


def render_macros_bar_chart(df: pl.DataFrame):
    base = (
        alt.Chart(df)
        .encode(
            x=alt.X(
                "metric_name:N", axis=alt.Axis(title=None, labels=False, ticks=False)
            ),
            y=alt.Y(
                "quantity:Q",
                title="Grams",
            ),
            color=alt.Color("metric_name:N", title="Macro"),
            tooltip=["metric_date:N", "metric_name:N", "quantity:Q"],
        )
        .properties(height=MACROS_BAR_HEIGHT)
    )

    bars = base.mark_bar()

    labels = base.mark_text(
        align="center", baseline="bottom", dy=-5, fontSize=11
    ).encode(text=alt.Text("quantity:Q", format=".0f"))

    layered = alt.layer(bars, labels)

    chart = (
        layered.facet(
            column=alt.Column(
                "metric_date:N",
                title=None,
            )
        )
        .resolve_scale(y="shared")
        .properties(title="Daily Macro Breakdown")
    )
    st.altair_chart(chart, use_container_width=True)


def render_altair_line_chart(df: pl.DataFrame, title: str):
    """Generate a line chart of the data and limit the y values to their min/max."""
    chart = (
        alt.Chart(df)
        .mark_line()
        .encode(
            x=alt.X("metric_date:N", title="Date"),
            y=alt.Y(
                "quantity:Q",
                title=title,
                scale=alt.Scale(domain=[df["quantity"].min(), df["quantity"].max()]),
            ),
        )
    )

    return st.altair_chart(chart)
