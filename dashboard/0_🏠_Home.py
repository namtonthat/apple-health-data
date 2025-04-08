import streamlit as st

st.set_page_config(page_title="🏠 Home", page_icon="🏡")
st.title("🏠 Nam Tonthat's Health Data")

st.markdown("Choose a dashboard:")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏋️ Exercises"):
        st.switch_page("pages/1_🏋️_Exercises.py")
with col2:
    if st.button("😴 Mental Health"):
        st.switch_page("pages/2_😴_Mental_Health.py")
with col3:
    if st.button("🍽️ Nutrition"):
        st.switch_page("pages/3_🍽️_Nutrition.py")
