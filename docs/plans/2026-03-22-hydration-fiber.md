# Hydration & Fiber in Nutrition Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add daily water intake and fiber to the Nutrition & Body page — both as columns in the Daily Nutrition table and as metric cards.

**Architecture:** `water_ml` and `fiber_g` already exist in `fct_daily_summary` (via `int_health__daily_nutrition`). No dbt changes needed. This is a UI-only addition to `2_Nutrition_&_Body.py`.

**Tech Stack:** Streamlit, Polars, Pandas (for Styler)

---

### Task 1: Add Fiber and Water to the Daily Nutrition table and metric cards

**Files:**
- Modify: `src/dashboard/pages/2_Nutrition_&_Body.py`

**Step 1: Add Fiber and Water metric cards**

In the left column macro metrics section (around line 69-75), add fiber and water cards. Change the 2x2 grid to include a third row:

After the existing `m1, m2` block with Protein/Carbs/Fat/Calories, add:

```python
            m3, m4 = st.columns(2)
            with m3:
                avg_fiber = macro_data["fiber_g"].mean() if "fiber_g" in macro_data.columns else None
                if avg_fiber is not None:
                    st.metric("Fiber", f"{avg_fiber:.0f}g")
            with m4:
                avg_water = macro_data["water_ml"].mean() if "water_ml" in macro_data.columns else None
                if avg_water is not None:
                    st.metric("Water", f"{avg_water:.0f}ml")
```

**Step 2: Extend the Daily Nutrition table**

In the table section (around line 143), update `nutrition_cols` to include `fiber_g` and `water_ml`:

Change:
```python
nutrition_cols = ["date", "protein_g", "carbs_g", "fat_g", "logged_calories"]
```
To:
```python
nutrition_cols = ["date", "protein_g", "carbs_g", "fat_g", "logged_calories", "fiber_g", "water_ml"]
```

Update the column rename (around line 156):
```python
col_names = ["Date", "Protein (g)", "Carbs (g)", "Fat (g)", "Calories"]
if "fiber_g" in display_table.columns:
    col_names.append("Fiber (g)")
if "water_ml" in display_table.columns:
    col_names.append("Water (ml)")
display_df.columns = col_names
```

Add formatting for the new columns:
```python
"Fiber (g)": "{:.0f}",
"Water (ml)": "{:.0f}",
```

**Step 3: Run lint**

Run: `uv run ruff check --fix src/dashboard/pages/2_Nutrition_\&_Body.py && uv run ruff format src/dashboard/pages/2_Nutrition_\&_Body.py`

**Step 4: Commit**

```bash
git add "src/dashboard/pages/2_Nutrition_&_Body.py"
git commit -m "feat: add fiber and water intake to Nutrition page"
```
