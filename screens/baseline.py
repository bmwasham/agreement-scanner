import streamlit as st


def render(state):
    st.header("Baseline — Control Group")
    st.caption("Previously accepted clauses, grouped by category. This is what every new scan is compared against.")

    entries = list(state["baseline_entries"].values())
    if not entries:
        st.info("No baseline entries yet. Accept clauses on the Review or Compare screen to build one up.")
        return

    by_category = {}
    for entry in entries:
        by_category.setdefault(entry.category, []).append(entry)

    for category in sorted(by_category):
        cat_entries = sorted(by_category[category], key=lambda e: e.date_added, reverse=True)
        st.subheader(f"{category} ({len(cat_entries)})")

        for entry in cat_entries:
            with st.container(border=True):
                st.write(entry.text)
                st.caption(f"Source: {entry.source} · Added {entry.date_added}")

                armed_key = "baseline_remove_arm"
                if state.get(armed_key) == entry.id:
                    matched_clauses = [
                        c for c in state["clauses"].values()
                        if c.matched_entry_text == entry.text
                    ]
                    st.warning(
                        f"Removing this entry affects **{len(matched_clauses)}** clause(s) "
                        f"across {len({c.agreement_id for c in matched_clauses})} document(s)."
                    )
                    col1, col2, col3 = st.columns(3)
                    if col1.button("Keep matches (promote them)", key=f"promote_{entry.id}", type="primary"):
                        st.info(
                            "This is the default, non-destructive path from spec §6: each matched "
                            "clause becomes its own independent baseline entry — nothing reverts to "
                            "pending. Full logic lands in Milestone 2 alongside real persistence."
                        )
                        state[armed_key] = None
                    if col2.button("Discard matches too", key=f"discard_{entry.id}"):
                        st.info(
                            "This is the explicit opt-in path from spec §6: affected clauses revert "
                            "to new/pending with an honest Undetermined Risk placeholder and a "
                            "match_invalidated flag. Full logic lands in Milestone 2."
                        )
                        state[armed_key] = None
                    if col3.button("Cancel", key=f"cancel_{entry.id}"):
                        state[armed_key] = None
                else:
                    if st.button("Remove", key=f"remove_{entry.id}"):
                        state[armed_key] = entry.id
