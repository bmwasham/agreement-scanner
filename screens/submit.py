from datetime import date

import streamlit as st

from models import Agreement, Clause
from utils import new_id


def render(state):
    st.header("Submit")
    st.caption("Paste an agreement, pick a category, and scan it against your baseline.")

    name = st.text_input("Document name", placeholder="e.g. Acme Inc. Terms of Service")

    categories = state["categories"]
    category_choice = st.selectbox("Category", options=categories + ["+ Add new category"])
    if category_choice == "+ Add new category":
        new_category = st.text_input("New category name")
    else:
        new_category = None

    source_url = st.text_input("Source URL (optional)")
    raw_text = st.text_area("Raw agreement text", height=300)

    scan_disabled = not name or not raw_text or (category_choice == "+ Add new category" and not new_category)

    if st.button("Scan", type="primary", disabled=scan_disabled):
        category = new_category.strip() if new_category else category_choice
        if new_category and category not in state["categories"]:
            state["categories"].append(category)

        agreement_id = new_id("ag")
        baseline_size = len([e for e in state["baseline_entries"].values() if e.category == category])

        state["agreements"][agreement_id] = Agreement(
            id=agreement_id,
            name=name,
            source_url=source_url or None,
            category=category,
            date_submitted=date.today(),
            date_reviewed=None,
            status="pending review",
            baseline_size_at_submission=baseline_size,
            digest=None,
        )

        # Milestone 1: canned placeholder clauses so navigation/state-sharing can be tested.
        # Real chunking + AI segmentation replaces this in Milestone 3.
        clause_1_id = new_id("cl")
        clause_2_id = new_id("cl")
        state["clauses"][clause_1_id] = Clause(
            id=clause_1_id,
            agreement_id=agreement_id,
            ref="§1",
            text=(raw_text.strip()[:200] or "(placeholder provision text)"),
            match_status="new",
            impact_rating="Medium",
            prevalence="Standard",
            rationale="Placeholder rationale — Milestone 1 has no AI comparison yet.",
            prevalence_rationale="Placeholder — Milestone 1 has no AI comparison yet.",
            confidence=0.5,
            disposition="pending",
        )
        state["clauses"][clause_2_id] = Clause(
            id=clause_2_id,
            agreement_id=agreement_id,
            ref="§2",
            text="Placeholder second provision for testing the Review/Compare layout.",
            match_status="new",
            impact_rating="Low",
            prevalence="Standard",
            rationale="Placeholder rationale.",
            prevalence_rationale="Placeholder rationale.",
            confidence=0.5,
            disposition="pending",
        )

        state["current_agreement_id"] = agreement_id
        st.success(f"Scanned “{name}” — 2 placeholder clauses created. Head to Review or Compare to see them.")
