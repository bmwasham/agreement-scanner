import streamlit as st

from fixtures import seed_state
from screens import baseline, compare, log as log_screen, review, submit

st.set_page_config(page_title="Agreement Scanner", layout="wide")


def init_state():
    if "initialized" not in st.session_state:
        for key, value in seed_state().items():
            st.session_state[key] = value
        st.session_state["initialized"] = True


init_state()

SCREENS = {
    "Baseline": baseline.render,
    "Submit": submit.render,
    "Review": review.render,
    "Compare": compare.render,
    "Log": log_screen.render,
}

st.sidebar.title("Agreement Scanner")
st.sidebar.caption("Milestone 1 — UI shell, dummy data, no AI or database yet.")
choice = st.sidebar.radio("Screen", list(SCREENS.keys()), key="nav_choice")

SCREENS[choice](st.session_state)
