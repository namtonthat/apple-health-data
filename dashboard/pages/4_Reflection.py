"""
Streamlit dashboard for apple-health-data
"""

from datetime import datetime

import streamlit as st
from helpers import (
    get_all_entries,
    init_db,
    insert_entry,
    load_questions_from_yaml,
    sidebar_datetime_filter,
)

# Sidebar date selection
today = datetime.today().date()
start_date, end_date = sidebar_datetime_filter()

st.title("Weekly Check-in Form")

init_db()
QUESTIONS = load_questions_from_yaml()

with st.form("weekly_checkin"):
    responses = {}
    for q in QUESTIONS:
        responses[q] = st.text_input(q)

    submitted = st.form_submit_button("Submit")

if submitted:
    now = datetime.now()

    for q, r in responses.items():
        insert_entry(now, "question", q)
        insert_entry(now, "response", r)

    st.success("Responses submitted!")

st.header("📋 Past Responses")

entries = get_all_entries()
if entries:
    grouped = {}
    for date, type_, content in entries:
        grouped.setdefault(date, []).append((type_, content))

    for date, items in sorted(grouped.items(), reverse=True):
        st.subheader(f"🗓️ {date.strftime('%Y-%m-%d %H:%M')}")

        for type_, content in items:
            if type_ == "question":
                st.markdown(f"**❓ {content}**")
            elif type_ == "response":
                st.markdown(f"📝 {content}")
            elif type_ == "coach-reflection":
                st.markdown(f"💬 _Coach: {content}_")

        with st.expander("➕ Add coach reflection"):  # noqa: RUF001
            reflection = st.text_input("Coach notes:", key=f"coach_{date}")
            if st.button("Save Reflection", key=f"btn_{date}"):
                insert_entry(date, "coach-reflection", reflection)
                st.rerun()
else:
    st.info("No entries yet. Submit the form to get started.")
