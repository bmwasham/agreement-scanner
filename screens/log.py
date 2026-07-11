from datetime import date

import streamlit as st


def render(state):
    st.header("Log")
    st.caption("Full scan history.")

    entries = sorted(
        state["review_log"].values(),
        key=lambda e: e.date_reviewed or date.min,
        reverse=True,
    )
    if not entries:
        st.info("No completed reviews yet.")
        return

    for entry in entries:
        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1, 1, 1])
            cols[0].markdown(f"**{entry.name}**")
            cols[1].caption(f"New: {entry.new_found}")
            cols[2].caption(f"Accepted: {entry.accepted}")
            cols[3].caption(f"Rejected: {entry.rejected}")
            cols[4].caption(f"Pending: {entry.pending}")
            if entry.source_url:
                st.caption(entry.source_url)
            st.caption(f"Reviewed {entry.date_reviewed}")

            armed_key = "log_delete_arm"
            if state.get(armed_key) == entry.id:
                st.warning(
                    "Deleting this scan record does not touch the baseline — baseline entries it "
                    "contributed stay put, and clauses elsewhere that matched them are unaffected. "
                    "(Real cross-reference counts land in Milestone 2 with SQLite persistence.)"
                )
                col1, col2 = st.columns(2)
                if col1.button("Confirm delete", key=f"confirm_delete_{entry.id}", type="primary"):
                    del state["review_log"][entry.id]
                    state[armed_key] = None
                    st.rerun()
                if col2.button("Cancel", key=f"cancel_delete_{entry.id}"):
                    state[armed_key] = None
            else:
                if st.button("Delete", key=f"delete_{entry.id}"):
                    state[armed_key] = entry.id
                    st.rerun()
