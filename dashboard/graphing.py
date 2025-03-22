import altair as alt
import polars as pl
import streamlit as st

MACROS_BAR_HEIGHT = 400


def render_macros_bar_chart(df: pl.DataFrame):
    chart_data = df.to_pandas()

    base = (
        alt.Chart(chart_data)
        .encode(
            x=alt.X(
                "metric_name:N", axis=alt.Axis(title=None, labels=False, ticks=False)
            ),
            y=alt.Y("quantity:Q", title="Grams"),
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
