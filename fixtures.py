"""Milestone 1 dummy data: enough variety to exercise every screen and sort/cluster rule."""
from datetime import date

from models import Agreement, BaselineEntry, Clause, DEFAULT_CATEGORIES, ReviewLogEntry


def seed_state():
    categories = list(DEFAULT_CATEGORIES)

    baseline_entries = {}
    for entry in [
        BaselineEntry(
            id="be_1",
            category="Terms of Service",
            text="We may modify these terms at any time; continued use constitutes acceptance.",
            source="Basecamp — Terms of Service (https://basecamp.com/terms)",
            date_added=date(2025, 1, 10),
        ),
        BaselineEntry(
            id="be_2",
            category="Terms of Service",
            text="Disputes will be resolved through binding arbitration on an individual basis.",
            source="Basecamp — Terms of Service (https://basecamp.com/terms)",
            date_added=date(2025, 1, 10),
        ),
        BaselineEntry(
            id="be_3",
            category="Privacy Policy",
            text="We retain account data for 90 days after account deletion before permanent removal.",
            source="Linear — Privacy Policy (https://linear.app/privacy)",
            date_added=date(2025, 2, 3),
        ),
    ]:
        baseline_entries[entry.id] = entry

    agreements = {
        "ag_1": Agreement(
            id="ag_1",
            name="Notion Terms of Service",
            source_url="https://notion.so/terms",
            category="Terms of Service",
            date_submitted=date(2025, 6, 1),
            date_reviewed=None,
            status="pending review",
            baseline_size_at_submission=2,
            digest=(
                "Two provisions are worth reading closely: an unusually broad license "
                "grant over content you upload, and a high-impact liability cap that goes "
                "further than typical practice. Everything else lines up with standard "
                "industry terms you've already accepted elsewhere.\n\n"
                "The rest of the document — the arbitration clause and the modification "
                "notice — is safe to skim; both match language you've reviewed before."
            ),
        ),
        "ag_2": Agreement(
            id="ag_2",
            name="Vercel Privacy Policy",
            source_url="https://vercel.com/privacy",
            category="Privacy Policy",
            date_submitted=date(2025, 5, 20),
            date_reviewed=date(2025, 5, 21),
            status="reviewed",
            baseline_size_at_submission=1,
            digest="Nothing new stood out here; the data retention language matches what you've already accepted, and the rest is standard boilerplate.",
        ),
    }

    clauses = {}
    for c in [
        Clause(
            id="cl_1",
            agreement_id="ag_1",
            ref="§3",
            text="You grant us a perpetual, irrevocable, worldwide license to use, reproduce, and create derivative works from any content you upload, for any purpose including training future models.",
            match_status="new",
            impact_rating="High",
            prevalence="Unusual",
            rationale="Grants far broader rights than a typical hosting license, including AI training use with no opt-out.",
            prevalence_rationale="Most ToS limit the license to operating the service itself; unrestricted downstream/training use is not typical.",
            confidence=0.88,
            disposition="pending",
        ),
        Clause(
            id="cl_2",
            agreement_id="ag_1",
            ref="§9",
            text="Our total liability for any claim is limited to the greater of $50 or fees paid in the past month.",
            match_status="new",
            impact_rating="High",
            prevalence="Unusual",
            rationale="Liability cap is unusually low relative to typical fee-based caps.",
            prevalence_rationale="Most comparable ToS cap liability at 12 months of fees, not 1.",
            confidence=0.81,
            disposition="pending",
        ),
        Clause(
            id="cl_3",
            agreement_id="ag_1",
            ref="§7",
            text="If any part of these terms is unenforceable, the remaining provisions stay in effect.",
            match_status="new",
            impact_rating="Inconsequential",
            prevalence="Standard",
            rationale="Standard severability boilerplate with no practical effect on you.",
            prevalence_rationale="Present in nearly every agreement of this type.",
            confidence=0.97,
            disposition="pending",
        ),
        Clause(
            id="cl_4",
            agreement_id="ag_1",
            ref="§11",
            text="We will provide notice of material changes through reasonable means, at our discretion.",
            match_status="new",
            impact_rating="Undetermined Risk",
            prevalence="Standard",
            rationale="\"Reasonable means\" and \"material\" are undefined; unclear what actually triggers notice.",
            prevalence_rationale="Vague notice language of this kind is common, even though the vagueness itself is genuine.",
            confidence=0.62,
            disposition="pending",
        ),
        Clause(
            id="cl_5",
            agreement_id="ag_1",
            ref="§12",
            text="We may modify these terms at any time; continued use of the service constitutes your acceptance of the revised terms.",
            match_status="matches_baseline",
            matched_entry_text=baseline_entries["be_1"].text,
            rationale="Same modification-and-continued-use mechanism as the accepted Basecamp entry.",
            confidence=0.93,
            disposition="pending",
        ),
        Clause(
            id="cl_6",
            agreement_id="ag_1",
            ref="§14",
            text="Any dispute arising from these terms will be resolved by binding arbitration, and you waive any right to a jury trial or class action.",
            match_status="matches_baseline",
            matched_entry_text=baseline_entries["be_2"].text,
            rationale="Same individual binding-arbitration mechanism as the accepted Basecamp entry.",
            confidence=0.9,
            disposition="pending",
        ),
        Clause(
            id="cl_7",
            agreement_id="ag_2",
            ref="§4",
            text="We retain account data for 90 days following account deletion before it is permanently removed from backups.",
            match_status="matches_baseline",
            matched_entry_text=baseline_entries["be_3"].text,
            rationale="Same 90-day retention window as the accepted Linear entry.",
            confidence=0.95,
            disposition="accepted",
            disposition_date=date(2025, 5, 21),
        ),
        Clause(
            id="cl_8",
            agreement_id="ag_2",
            ref="§6",
            text="We may share aggregated, de-identified usage statistics with partners for benchmarking purposes.",
            match_status="new",
            impact_rating="Low",
            prevalence="Standard",
            rationale="De-identified aggregate sharing has minimal individual privacy impact.",
            prevalence_rationale="Common practice across the industry.",
            confidence=0.9,
            disposition="accepted",
            disposition_date=date(2025, 5, 21),
        ),
    ]:
        clauses[c.id] = c

    review_log = {
        "rl_1": ReviewLogEntry(
            id="rl_1",
            agreement_id="ag_2",
            name="Vercel Privacy Policy",
            source_url="https://vercel.com/privacy",
            date_reviewed=date(2025, 5, 21),
            new_found=1,
            accepted=1,
            rejected=0,
            pending=0,
        ),
    }

    return {
        "categories": categories,
        "agreements": agreements,
        "clauses": clauses,
        "baseline_entries": baseline_entries,
        "review_log": review_log,
    }
