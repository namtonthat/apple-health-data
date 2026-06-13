"""Performance Insights — how recovery and nutrition relate to training.

Day-level correlations over the full available history (recovery/nutrition data
goes back further than the 90-day pages), plus rest-vs-training comparisons and
long-run trends. Correlation is not causation and daily self-tracked data is
noisy, so weak coefficients are expected — the captions read each one plainly.
"""

import altair as alt
import polars as pl
import streamlit as st

st.set_page_config(page_title="📊 Performance Insights", page_icon="📊", layout="wide")

from dashboard.data import load_daily_summary  # noqa: E402

MIN_PAIRS = 10  # don't report a correlation computed on fewer than this many days


def pearson(df: pl.DataFrame, x: str, y: str) -> tuple[int, float | None]:
    """Pearson r over rows where both columns are present."""
    if x not in df.columns or y not in df.columns:
        return 0, None
    sub = df.select([x, y]).drop_nulls()
    if sub.height < MIN_PAIRS:
        return sub.height, None
    r = sub.select(pl.corr(x, y)).item()
    return sub.height, (round(r, 2) if r is not None else None)


def strength_label(r: float | None) -> str:
    """Plain-English read of a correlation coefficient."""
    if r is None:
        return "not enough data"
    a = abs(r)
    direction = "positive" if r > 0 else "negative"
    if a < 0.2:
        return "negligible"
    if a < 0.4:
        return f"weak {direction}"
    if a < 0.6:
        return f"moderate {direction}"
    return f"strong {direction}"


st.title("📊 Performance Insights")
st.caption(
    "How sleep, recovery and nutrition relate to your training. "
    "Computed across all available history."
)

df = load_daily_summary()

if df.is_empty():
    st.info("No data available yet.")
    st.stop()

df = df.with_columns(pl.col("date").cast(pl.Date)).sort("date")

# Lagged recovery columns: what happened the NIGHT AFTER a given day.
df = df.with_columns(
    [
        pl.col("hrv_ms").shift(-1).alias("hrv_next"),
        pl.col("resting_hr_bpm").shift(-1).alias("rhr_next"),
        pl.col("sleep_hours").shift(-1).alias("sleep_next"),
    ]
)

train = df.filter(pl.col("had_strength_workout"))

# =============================================================================
# 1. Correlation tables
# =============================================================================
st.header("What moves with what")

same_day = [
    ("Sleep (h) → training volume", "sleep_hours", "total_volume_kg", train),
    ("Deep sleep (h) → training volume", "sleep_deep_hours", "total_volume_kg", train),
    ("HRV (ms) → training volume", "hrv_ms", "total_volume_kg", train),
    ("HRV (ms) → session RPE", "hrv_ms", "avg_rpe", train),
    ("Resting HR → training volume", "resting_hr_bpm", "total_volume_kg", train),
    ("Protein (g) → training volume", "protein_g", "total_volume_kg", train),
    ("Calories → training volume", "logged_calories", "total_volume_kg", train),
]
lagged = [
    ("Training volume → next-night sleep", "total_volume_kg", "sleep_next", df),
    ("Training volume → next-day HRV", "total_volume_kg", "hrv_next", df),
    ("Training volume → next-day resting HR", "total_volume_kg", "rhr_next", df),
    ("Workout duration → next-day HRV", "workout_duration_minutes", "hrv_next", df),
]


def corr_rows(specs: list) -> pl.DataFrame:
    out = []
    for label, x, y, frame in specs:
        n, r = pearson(frame, x, y)
        out.append({"Relationship": label, "r": r, "Days": n, "Read": strength_label(r)})
    return pl.DataFrame(out)


col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Recovery & fuel → same-day training")
    st.dataframe(
        corr_rows(same_day).to_pandas(),
        hide_index=True,
        use_container_width=True,
        column_config={
            "r": st.column_config.NumberColumn("r", format="%.2f", width="small"),
            "Days": st.column_config.NumberColumn("Days", width="small"),
        },
    )
with col_b:
    st.subheader("Training load → next-day recovery")
    st.dataframe(
        corr_rows(lagged).to_pandas(),
        hide_index=True,
        use_container_width=True,
        column_config={
            "r": st.column_config.NumberColumn("r", format="%.2f", width="small"),
            "Days": st.column_config.NumberColumn("Days", width="small"),
        },
    )

st.caption(
    "*r ranges −1 to +1. |r| < 0.2 is negligible. Day-to-day self-tracked data is "
    "noisy, so the signal usually lives in the long-run trends below, not single days.*"
)

# =============================================================================
# 2. Rest vs training day recovery
# =============================================================================
st.header("Rest days vs training days")
rec = df.filter(pl.col("sleep_hours").is_not_null() | pl.col("hrv_ms").is_not_null())
if rec.height > 0:
    comp = (
        rec.group_by("had_strength_workout")
        .agg(
            pl.len().alias("days"),
            pl.col("sleep_hours").mean().alias("sleep_h"),
            pl.col("hrv_ms").mean().alias("hrv"),
            pl.col("resting_hr_bpm").mean().alias("rhr"),
            pl.col("steps").mean().alias("steps"),
        )
        .sort("had_strength_workout")
    )
    lookup = {row["had_strength_workout"]: row for row in comp.to_dicts()}

    def _fmt(group: bool, key: str, fmt: str) -> str:
        row = lookup.get(group)
        if row is None or row[key] is None:
            return "—"
        return f"{row[key]:{fmt}}"

    c1, c2, c3, c4 = st.columns(4)
    for col, key, label, fmt in [
        (c1, "sleep_h", "Avg sleep", ".2f"),
        (c2, "hrv", "Avg HRV", ".0f"),
        (c3, "rhr", "Avg resting HR", ".0f"),
        (c4, "steps", "Avg steps", ",.0f"),
    ]:
        with col:
            st.metric(
                f"{label} — training",
                _fmt(True, key, fmt),
                delta=f"rest: {_fmt(False, key, fmt)}",
                delta_color="off",
            )
    st.caption("*Near-identical rest vs training recovery means training isn't tanking recovery.*")

# =============================================================================
# 3. Long-run monthly trends
# =============================================================================
st.header("Monthly trends")
monthly = (
    df.with_columns(pl.col("date").dt.truncate("1mo").alias("month"))
    .group_by("month")
    .agg(
        pl.col("weight_kg").mean().round(1).alias("Weight (kg)"),
        pl.col("logged_calories").mean().round(0).alias("Calories"),
        pl.col("protein_g").mean().round(0).alias("Protein (g)"),
        pl.col("sleep_hours").mean().round(2).alias("Sleep (h)"),
        pl.col("hrv_ms").mean().round(0).alias("HRV (ms)"),
    )
    .sort("month")
    .filter(
        pl.col("Weight (kg)").is_not_null()
        | pl.col("Calories").is_not_null()
        | pl.col("Sleep (h)").is_not_null()
    )
)

if monthly.height > 0:
    metric_choice = st.selectbox(
        "Metric",
        ["Weight (kg)", "Calories", "Protein (g)", "Sleep (h)", "HRV (ms)"],
    )
    chart_df = (
        monthly.with_columns(pl.col("month").dt.strftime("%Y-%m").alias("Month"))
        .select(["Month", metric_choice])
        .drop_nulls()
        .to_pandas()
    )
    if not chart_df.empty:
        line = (
            alt.Chart(chart_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("Month:N", sort=None, title="Month"),
                y=alt.Y(f"{metric_choice}:Q", title=metric_choice, scale=alt.Scale(zero=False)),
            )
        )
        st.altair_chart(line, use_container_width=True)

    st.subheader("Monthly table")
    st.dataframe(
        monthly.with_columns(pl.col("month").dt.strftime("%Y-%m").alias("Month"))
        .select(["Month", "Weight (kg)", "Calories", "Protein (g)", "Sleep (h)", "HRV (ms)"])
        .sort("Month", descending=True)
        .to_pandas(),
        hide_index=True,
        use_container_width=True,
    )

st.divider()
st.caption("*Correlations use all overlapping days; weak coefficients are normal at daily grain.*")
