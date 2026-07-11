import streamlit as st

from screens._shared import render_clause_card
from utils import clause_priority_key, clauses_for_agreement, select_agreement


def render(state):
    st.header("Compare")
    agreement = select_agreement(state, key_suffix="compare")
    if agreement is None:
        return

    clauses = clauses_for_agreement(state, agreement.id)
    clause_ids = {c.id for c in clauses}

    order_key = f"compare_order_{agreement.id}"
    cached_order = state.get(order_key)
    if not cached_order or set(cached_order) != clause_ids:
        cached_order = [c.id for c in sorted(clauses, key=clause_priority_key)]
        state[order_key] = cached_order

    st.caption("Whole document, top to bottom, sorted by priority once — order won't reshuffle as you act.")

    for clause_id in cached_order:
        clause = state["clauses"][clause_id]
        render_clause_card(state, clause, key_prefix="compare", muted=clause.disposition != "pending")
