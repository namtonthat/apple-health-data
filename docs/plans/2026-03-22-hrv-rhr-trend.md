# HRV & RHR Trend Chart Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a dual-line trend chart showing HRV and Resting Heart Rate over time to the Recovery page, between the Sleep section and the Meditation/Steps section.

**Architecture:** No dbt changes needed — `resting_hr_bpm` and `hrv_ms` already flow through `fct_daily_summary` to the dashboard via `load_daily_summary()`. This is purely a UI addition to `1_Recovery.py`.

**Tech Stack:** Streamlit, Altair (dual-axis line chart), Polars

---

### Task 1: Add HRV & RHR section to Recovery page

**Files:**
- Modify: `src/dashboard/pages/1_Recovery.py:371-373` (between Sleep divider and Meditation/Steps section)

**Step 1: Add the Cardiovascular Health section**

Insert the following block between line 373 (`st.divider()`) and line 375 (`# Meditation & Steps`):

```python
# =============================================================================
# Cardiovascular Health — HRV & RHR Trends
# =============================================================================
st.header("Cardiovascular Health")

has_rhr = "resting_hr_bpm" in df_daily.columns and df_daily["resting_hr_bpm"].drop_nulls().len() > 0
has_hrv = "hrv_ms" in df_daily.columns and df_daily["hrv_ms"].drop_nulls().len() > 0

if has_rhr or has_hrv:
    cardio_data = df_daily.filter(
        pl.col("resting_hr_bpm").is_not_null() | pl.col("hrv_ms").is_not_null()
    )

    # Metric cards
    cv1, cv2, cv3, cv4 = st.columns(4)
    if has_rhr:
        rhr_data = cardio_data.filter(pl.col("resting_hr_bpm").is_not_null())
        with cv1:
            st.metric("Avg RHR", f"{rhr_data['resting_hr_bpm'].mean():.0f} bpm")
        with cv2:
            st.metric("RHR Range", f"{rhr_data['resting_hr_bpm'].min():.0f}–{rhr_data['resting_hr_bpm'].max():.0f}")
    if has_hrv:
        hrv_data = cardio_data.filter(pl.col("hrv_ms").is_not_null())
        with cv3:
            st.metric("Avg HRV", f"{hrv_data['hrv_ms'].mean():.0f} ms")
        with cv4:
            st.metric("HRV Range", f"{hrv_data['hrv_ms'].min():.0f}–{hrv_data['hrv_ms'].max():.0f}")

    # Dual line chart
    if cardio_data.height > 0:
        chart_data = (
            cardio_data.with_columns(
                pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("Date")
            )
            .select(["Date", "resting_hr_bpm", "hrv_ms"])
            .to_pandas()
        )

        col_rhr_chart, col_hrv_chart = st.columns(2)

        with col_rhr_chart:
            st.subheader("Resting Heart Rate")
            rhr_line = (
                alt.Chart(chart_data.dropna(subset=["resting_hr_bpm"]))
                .mark_line(point=True, color="#EF553B")
                .encode(
                    x=alt.X("Date:N", sort=None, title="Date"),
                    y=alt.Y("resting_hr_bpm:Q", title="BPM", scale=alt.Scale(zero=False)),
                )
            )
            rhr_text = (
                alt.Chart(chart_data.dropna(subset=["resting_hr_bpm"]))
                .mark_text(dy=-10, fontSize=11, color="white")
                .encode(
                    x=alt.X("Date:N", sort=None),
                    y=alt.Y("resting_hr_bpm:Q"),
                    text=alt.Text("resting_hr_bpm:Q", format=".0f"),
                )
            )
            st.altair_chart(rhr_line + rhr_text, width="stretch")

        with col_hrv_chart:
            st.subheader("Heart Rate Variability")
            hrv_line = (
                alt.Chart(chart_data.dropna(subset=["hrv_ms"]))
                .mark_line(point=True, color="#636EFA")
                .encode(
                    x=alt.X("Date:N", sort=None, title="Date"),
                    y=alt.Y("hrv_ms:Q", title="ms", scale=alt.Scale(zero=False)),
                )
            )
            hrv_text = (
                alt.Chart(chart_data.dropna(subset=["hrv_ms"]))
                .mark_text(dy=-10, fontSize=11, color="white")
                .encode(
                    x=alt.X("Date:N", sort=None),
                    y=alt.Y("hrv_ms:Q"),
                    text=alt.Text("hrv_ms:Q", format=".0f"),
                )
            )
            st.altair_chart(hrv_line + hrv_text, width="stretch")

    st.caption(
        "*Lower RHR and higher HRV indicate better cardiovascular fitness and recovery readiness.*"
    )
else:
    st.info("No heart rate data available for selected period")

st.divider()
```

**Step 2: Run lint**

Run: `uv run ruff check --fix src/dashboard/pages/1_Recovery.py && uv run ruff format src/dashboard/pages/1_Recovery.py`

**Step 3: Verify dashboard loads**

Run: `uv run python -c "import ast; ast.parse(open('src/dashboard/pages/1_Recovery.py').read()); print('OK')"`

**Step 4: Commit**

```bash
git add src/dashboard/pages/1_Recovery.py
git commit -m "feat: add HRV & RHR trend charts to Recovery page"
```
