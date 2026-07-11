import streamlit as st

from screens._shared import render_clause_card, render_cluster
from utils import clause_priority_key, clauses_for_agreement, is_low_priority_clause, select_agreement


def render(state):
    st.header("Review")
    agreement = select_agreement(state, key_suffix="review")
    if agreement is None:
        return

    clauses = clauses_for_agreement(state, agreement.id)

    needs_attention = sorted(
        (c for c in clauses if c.match_status == "new" and c.disposition == "pending" and not is_low_priority_clause(c)),
        key=clause_priority_key,
    )
    cluster = [
        c for c in clauses
        if c.match_status == "new" and c.disposition == "pending" and is_low_priority_clause(c)
    ]
    dispositioned = [c for c in clauses if c.disposition in ("accepted", "rejected")]
    matched_pending = [c for c in clauses if c.match_status == "matches_baseline" and c.disposition == "pending"]

    st.subheader(f"Needs attention ({len(needs_attention)})")
    if not needs_attention:
        st.caption("Nothing needs individual attention right now.")
    for clause in needs_attention:
        render_clause_card(state, clause, key_prefix="review")

    st.subheader(f"Low-priority cluster ({len(cluster)})")
    if not cluster:
        st.caption("No standard, low-impact clauses pending.")
    else:
        with st.expander("Standard + Low/Inconsequential clauses — safe to bulk-review", expanded=False):
            render_cluster(state, agreement, cluster, key_prefix="review")

    if dispositioned:
        with st.expander(f"Already decided ({len(dispositioned)})"):
            for clause in dispositioned:
                render_clause_card(state, clause, key_prefix="review", muted=True)

    show_matched = st.toggle(
        f"Show clauses matched to baseline ({len(matched_pending)})",
        key="review_show_matched",
    )
    if show_matched:
        for clause in matched_pending:
            render_clause_card(state, clause, key_prefix="review")
