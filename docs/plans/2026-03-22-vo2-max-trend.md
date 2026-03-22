# VO2 Max Trend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a VO2 Max trend line chart with current value card to the Recovery page, inside the new Cardiovascular Health section (after HRV/RHR charts).

**Architecture:** `vo2_max` already flows through `fct_daily_summary`. This is a UI-only addition. VO2 Max updates less frequently than RHR/HRV (Apple Watch recalculates it after outdoor walks/runs), so expect gaps in the data.

**Tech Stack:** Streamlit, Altair, Polars

---

### Task 1: Add VO2 Max chart to the Cardiovascular Health section

**Files:**
- Modify: `src/dashboard/pages/1_Recovery.py` — inside the Cardiovascular Health section, after the RHR/HRV charts, before the caption

**Step 1: Add VO2 Max sub-section**

After the `col_hrv_chart` block and before the `st.caption(...)` line in the Cardiovascular Health section, add:

```python
    # VO2 Max trend (separate row — updates less frequently)
    has_vo2 = "vo2_max" in df_daily.columns and df_daily["vo2_max"].drop_nulls().len() > 0
    if has_vo2:
        vo2_data = cardio_data.filter(pl.col("vo2_max").is_not_null())
        if vo2_data.height > 0:
            st.subheader("VO2 Max")
            vo2_1, vo2_2, vo2_3 = st.columns(3)
            latest_vo2 = float(vo2_data.sort("date", descending=True)["vo2_max"].head(1).item())
            with vo2_1:
                st.metric("Current", f"{latest_vo2:.1f} ml/kg/min")
            with vo2_2:
                st.metric("Average", f"{vo2_data['vo2_max'].mean():.1f} ml/kg/min")
            with vo2_3:
                st.metric(
                    "Range",
                    f"{vo2_data['vo2_max'].min():.1f}–{vo2_data['vo2_max'].max():.1f}",
                )

            vo2_chart = (
                vo2_data.with_columns(
                    pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("Date")
                )
                .select(["Date", "vo2_max"])
                .to_pandas()
            )

            line = (
                alt.Chart(vo2_chart)
                .mark_line(point=True, color="#00CC96")
                .encode(
                    x=alt.X("Date:N", sort=None, title="Date"),
                    y=alt.Y("vo2_max:Q", title="ml/kg/min", scale=alt.Scale(zero=False)),
                )
            )
            text = (
                alt.Chart(vo2_chart)
                .mark_text(dy=-10, fontSize=11, color="white")
                .encode(
                    x=alt.X("Date:N", sort=None),
                    y=alt.Y("vo2_max:Q"),
                    text=alt.Text("vo2_max:Q", format=".1f"),
                )
            )
            st.altair_chart(line + text, width="stretch")
```

**Step 2: Run lint**

Run: `uv run ruff check --fix src/dashboard/pages/1_Recovery.py && uv run ruff format src/dashboard/pages/1_Recovery.py`

**Step 3: Commit**

```bash
git add src/dashboard/pages/1_Recovery.py
git commit -m "feat: add VO2 Max trend chart to Recovery page"
```
