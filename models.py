"""Data model for Agreement Scanner, mirroring the spec's SQLite schema (§1)."""
from dataclasses import dataclass
from datetime import date
from typing import Optional

IMPACT_RATINGS = ["High", "Medium", "Low", "Inconsequential", "Undetermined Risk"]
PREVALENCE_RATINGS = ["Standard", "Unusual"]
DISPOSITIONS = ["pending", "accepted", "rejected"]
MATCH_STATUSES = ["new", "matches_baseline"]
AGREEMENT_STATUSES = ["pending review", "reviewed"]

DEFAULT_CATEGORIES = ["Terms of Service", "Privacy Policy"]


@dataclass
class Agreement:
    id: str
    name: str
    source_url: Optional[str]
    category: str
    date_submitted: date
    date_reviewed: Optional[date]
    status: str
    baseline_size_at_submission: int
    digest: Optional[str] = None


@dataclass
class Clause:
    id: str
    agreement_id: str
    ref: str
    text: str
    match_status: str
    impact_rating: Optional[str] = None
    prevalence: Optional[str] = None
    matched_entry_text: Optional[str] = None
    rationale: str = ""
    prevalence_rationale: str = ""
    confidence: Optional[float] = None
    disposition: str = "pending"
    disposition_date: Optional[date] = None
    ai_failed: bool = False
    match_invalidated: bool = False


@dataclass
class BaselineEntry:
    id: str
    category: str
    text: str
    source: str
    date_added: date


@dataclass
class ReviewLogEntry:
    id: str
    agreement_id: str
    name: str
    source_url: Optional[str]
    date_reviewed: Optional[date]
    new_found: int
    accepted: int
    rejected: int
    pending: int
