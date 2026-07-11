"""Pure helper functions shared across screens: id generation, priority sort, clustering."""
import uuid
from datetime import date

import streamlit as st

from models import BaselineEntry, Clause

_IMPACT_TIER = {
    "High": 0,
    "Undetermined Risk": 0,
    "Medium": 1,
    "Low": 2,
    "Inconsequential": 2,
}


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def clause_priority_key(clause: Clause):
    """Lower sorts first. Impact tier primary, Unusual-before-Standard tiebreaker (spec §3)."""
    impact_tier = _IMPACT_TIER.get(clause.impact_rating, 3)
    unusual_first = 0 if clause.prevalence == "Unusual" else 1
    return (impact_tier, unusual_first)


def is_low_priority_clause(clause: Clause) -> bool:
    """Cluster-eligible only if Standard AND (Low or Inconsequential) — spec §3/§6 tech doc."""
    return clause.prevalence == "Standard" and clause.impact_rating in ("Low", "Inconsequential")


def clauses_for_agreement(state, agreement_id: str):
    return [c for c in state["clauses"].values() if c.agreement_id == agreement_id]


def agreements_sorted(state):
    return sorted(state["agreements"].values(), key=lambda a: a.date_submitted, reverse=True)


def select_agreement(state, key_suffix: str):
    """Shared document picker + persistent context header, used by Review and Compare."""
    agreements = agreements_sorted(state)
    if not agreements:
        st.info("No agreements yet — submit one on the Submit screen first.")
        return None

    if "current_agreement_id" not in state or state["current_agreement_id"] not in state["agreements"]:
        state["current_agreement_id"] = agreements[0].id

    labels = {a.id: f"{a.name} · {a.category} · {a.status}" for a in agreements}
    ids = [a.id for a in agreements]
    current_index = ids.index(state["current_agreement_id"])

    chosen = st.selectbox(
        "Document",
        options=ids,
        format_func=lambda aid: labels[aid],
        index=current_index,
        key=f"agreement_picker_{key_suffix}",
    )
    state["current_agreement_id"] = chosen
    agreement = state["agreements"][chosen]

    st.caption(
        f"**{agreement.name}** — {agreement.category} — submitted {agreement.date_submitted} "
        f"— status: {agreement.status}"
    )
    st.divider()
    return agreement


def _citation_for(agreement) -> str:
    if agreement.source_url:
        return f"{agreement.name} ({agreement.source_url})"
    return agreement.name


def accept_clause(state, clause: Clause):
    """Accept -> baseline entry created (spec §2, tech doc §3). Dedup by exact text within category."""
    clause.disposition = "accepted"
    clause.disposition_date = date.today()

    if clause.match_status == "new":
        agreement = state["agreements"][clause.agreement_id]
        already_exists = any(
            e.category == agreement.category and e.text == clause.text
            for e in state["baseline_entries"].values()
        )
        if not already_exists:
            entry_id = new_id("be")
            state["baseline_entries"][entry_id] = BaselineEntry(
                id=entry_id,
                category=agreement.category,
                text=clause.text,
                source=_citation_for(agreement),
                date_added=date.today(),
            )


def reject_clause(state, clause: Clause):
    clause.disposition = "rejected"
    clause.disposition_date = date.today()
