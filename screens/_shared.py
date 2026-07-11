"""Rendering shared between Review and Compare — same data, same actions, same clause card."""
import streamlit as st

from utils import accept_clause, reject_clause

_IMPACT_COLOR = {
    "High": "red",
    "Undetermined Risk": "orange",
    "Medium": "orange",
    "Low": "blue",
    "Inconsequential": "gray",
}


def render_clause_card(state, clause, key_prefix: str, muted: bool = False):
    with st.container(border=True):
        header_cols = st.columns([3, 1, 1])
        header_cols[0].markdown(f"**{clause.ref}**")

        if clause.match_status == "matches_baseline":
            header_cols[1].markdown(":green[Matches baseline]")
        else:
            color = _IMPACT_COLOR.get(clause.impact_rating, "gray")
            header_cols[1].markdown(f":{color}[{clause.impact_rating}]")
            header_cols[2].markdown(f"_{clause.prevalence}_" if clause.prevalence else "")

        if clause.match_invalidated:
            st.warning("This match was invalidated by a baseline entry removal — needs a fresh look, not an ordinary first-time miss.")
        if clause.ai_failed:
            st.warning("AI comparison failed for this clause — Undetermined Risk shown as an honest fallback, not a guess.")

        st.write(clause.text)

        if clause.match_status == "matches_baseline" and clause.matched_entry_text:
            st.caption(f"Matched baseline text: “{clause.matched_entry_text}”")
        if clause.rationale:
            st.caption(f"Rationale: {clause.rationale}")
        if clause.prevalence_rationale:
            st.caption(f"Prevalence rationale: {clause.prevalence_rationale}")
        if clause.confidence is not None:
            st.caption(f"Confidence: {clause.confidence:.0%}")

        if clause.disposition == "pending":
            btn_cols = st.columns([1, 1, 6])
            if btn_cols[0].button("Accept", key=f"{key_prefix}_accept_{clause.id}", type="primary"):
                accept_clause(state, clause)
                st.rerun()
            if btn_cols[1].button("Reject", key=f"{key_prefix}_reject_{clause.id}"):
                reject_clause(state, clause)
                st.rerun()
        else:
            label = "Accepted" if clause.disposition == "accepted" else "Rejected"
            st.caption(f"{'~~' if muted else ''}{label} on {clause.disposition_date}{'~~' if muted else ''}")


def render_cluster(state, agreement, cluster_clauses, key_prefix: str):
    mode_key = f"{key_prefix}_cluster_mode_{agreement.id}"
    mode = st.radio(
        "How do you want to review these?",
        options=["As a group (recommended)", "Individually"],
        index=None,
        key=mode_key,
        horizontal=True,
    )

    if mode is None:
        st.caption("Choose a mode to reveal these clauses — there's no default, both are equally valid.")
        return

    if mode == "Individually":
        for clause in cluster_clauses:
            render_clause_card(state, clause, key_prefix=key_prefix, muted=False)
        return

    expand_key = f"{key_prefix}_cluster_expanded_{agreement.id}"
    expanded = st.checkbox(f"Show all {len(cluster_clauses)} clauses in this group", key=expand_key)
    if not expanded:
        st.caption("Expand the group to see every clause before bulk-accepting — nothing gets accepted unseen.")
        return

    for clause in cluster_clauses:
        render_clause_card(state, clause, key_prefix=key_prefix, muted=False)

    if st.button(f"Accept all {len(cluster_clauses)} shown above", key=f"{key_prefix}_accept_all_{agreement.id}", type="primary"):
        for clause in cluster_clauses:
            if clause.disposition == "pending":
                accept_clause(state, clause)
        st.rerun()
