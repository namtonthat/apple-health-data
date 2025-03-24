"""
Streamlit dashboard for apple-health-data
"""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="🤔 Reflection",
    page_icon="🤔",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🤔 Exercise")

if not st.experimental_user.is_logged_in:
    if st.button("Log in with Google"):
        st.login()
    st.stop()

if st.button("Log out"):
    st.logout()
st.markdown(f"Welcome! {st.experimental_user.name}")

# Sidebar date selection
# today = datetime.today().date()
# start_date, end_date = sidebar_date_filter()
#
#
# try:
#     filtered_reflections = load_filtered_s3_data(
#         conf.key_reflections,
#         start_date,
#         end_date,
#     )
#     # Load configuration
#     kpi_config = load_kpi_config()
#
# except Exception as e:
#     st.error(f"Error loading data: {e}")
#     st.stop()
#
# # ---------------------- AVERAGE activity ----------------------
# try:
#     st.write(filtered_reflections)
# except Exception as e:
#     st.error(f"Error computing macro KPIs: {e}")
