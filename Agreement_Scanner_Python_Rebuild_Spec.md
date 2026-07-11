# Agreement Scanner — Python Rebuild Specification

This is a complete, self-contained brief for rebuilding Agreement Scanner as
a local Python application. It captures every design decision, algorithm,
and hard-won lesson from the original Claude-artifact build, so none of it
needs rediscovering. Hand this document to a fresh Claude Code session (or
paste it as the opening message of a new chat) as the starting brief.

---

## 0. Context and intent

Agreement Scanner is a personal tool for reviewing legal agreements (Terms
of Service, Privacy Policies) efficiently without ever agreeing to
something unread. Core mechanism: build a **baseline** of previously
accepted terms; compare every new document against it; surface only what's
genuinely new for review, with AI-assigned Impact and Prevalence ratings;
let the user accept/reject with full visibility into every action, never a
silent bulk approval.

**Recommended stack:** Python + **Streamlit**. Reasoning: this app is
forms, lists, buttons, and text — not real-time or highly interactive in a
way that needs a custom frontend. Streamlit gives a local, runnable-with-one-command
(`streamlit run app.py`) web UI, entirely in Python, with minimal
frontend code to write or maintain. Alternative: a lightweight Flask/FastAPI
backend with a simple HTML/JS frontend, if more UI control is wanted later
— but start with Streamlit unless there's a specific reason not to.

**Persistence:** local SQLite database (or plain JSON files if simplicity
is preferred over query power) instead of browser storage. No 5MB-per-key
ceiling to worry about.

**AI calls:** the `anthropic` Python SDK, with a real API key
(`ANTHROPIC_API_KEY` environment variable). **Cost note:** unlike the
Claude-artifact version (which used the user's existing Claude.ai usage
allowance), this will incur real, metered per-token API costs. A full ToS
scan makes one API call per ~2000-character chunk plus one digest call —
budget accordingly.

---

## 1. Data model

Translate directly to SQLite tables (or dataclasses + JSON files):

**agreements**
| field | type | notes |
|---|---|---|
| id | text (PK) | |
| name | text | |
| source_url | text, nullable | |
| category | text | |
| date_submitted | date | |
| date_reviewed | date, nullable | |
| status | text | "pending review" \| "reviewed" |
| baseline_size_at_submission | int | baseline count in this category at scan time |
| digest | text, nullable | |

**clauses**
| field | type | notes |
|---|---|---|
| id | text (PK) | |
| agreement_id | text (FK) | |
| ref | text | e.g. "§7" |
| text | text | verbatim extracted provision |
| match_status | text | "new" \| "matches_baseline" |
| impact_rating | text, nullable | High/Medium/Low/Inconsequential/Undetermined Risk |
| prevalence | text, nullable | Standard \| Unusual |
| matched_entry_text | text, nullable | snapshot, not a live FK |
| rationale | text | |
| prevalence_rationale | text | |
| confidence | float, nullable | |
| disposition | text | pending \| accepted \| rejected |
| disposition_date | date, nullable | |
| ai_failed | bool | |
| match_invalidated | bool | |

**baseline_entries**
| field | type | notes |
|---|---|---|
| id | text (PK) | |
| category | text | |
| text | text | |
| source | text | human-readable citation string, e.g. "Basecamp (https://...)" — **not** a foreign key to any agreement, by design (see §6) |
| date_added | date | |

**review_log**
| field | type | notes |
|---|---|---|
| id | text (PK) | |
| agreement_id | text (FK) | |
| name, source_url, date_reviewed | | |
| new_found, accepted, rejected, pending | int | |

**Critical design constraint:** `baseline_entries.source` must remain a
plain string, never a foreign key to `agreements.id`. This is what makes
baseline entries survive independently of the scan record that produced
them — do not "improve" this into a real foreign key relationship, it would
break the intentional design in §6.

---

## 2. The AI comparison engine

### 2.1 Chunking
Split raw agreement text into ~2000-character chunks at paragraph
boundaries (blank-line-separated), greedily packing paragraphs until the
limit, never splitting a paragraph across chunks if avoidable.

### 2.2 Per-chunk prompt
System prompt (adapt directly):

> You are the comparison engine inside a personal agreement-review tool.
> You are given a SECTION of raw text from a newly submitted agreement (it
> may be a partial excerpt of a longer document) and a BASELINE of
> previously accepted clauses for the same category.
>
> STEP 1 — Segment the section into discrete PROVISIONS. Each provision
> should represent one distinct legal concept, obligation, right, or
> disclosure. Real agreements often pack multiple unrelated concepts into a
> single paragraph — split those into separate provisions. Conversely, do
> not split a single rule and its immediate qualifying clause into two
> fragments if they only make sense read together. Provision/section-level
> granularity, not sentence-level, not whole-paragraph-level.
>
> STEP 2 — For each provision: TEXT (exact verbatim, no paraphrasing),
> MATCH_STATUS (matches_baseline or new), MATCHED_BASELINE_ID (if matched),
> IMPACT_RATING (High/Medium/Low/Inconsequential/Undetermined Risk — only
> if new; Undetermined Risk only for genuine vagueness, not unfavorability),
> PREVALENCE (Standard/Unusual — only if new; judged from general knowledge
> of how these documents typically read, not from the given baseline),
> RATIONALE, PREVALENCE_RATIONALE, CONFIDENCE (0–1).

**Output format: plain delimited text, not JSON.** This is a deliberate,
hard-won decision — see the Technical Documentation §4 for why JSON
repeatedly failed (unescaped quotes in legal text breaking `JSON.parse`
mid-response). Use unique sentinel markers:
```
<<<PROVISION>>>
<<<TEXT>>>
...
<<<MATCH_STATUS>>>
...
<<<MATCHED_BASELINE_ID>>>
...
<<<IMPACT_RATING>>>
...
<<<PREVALENCE>>>
...
<<<RATIONALE>>>
...
<<<PREVALENCE_RATIONALE>>>
...
<<<CONFIDENCE>>>
...
<<<END_PROVISION>>>
```
Parse leniently: split on `<<<PROVISION>>>`, extract each field by finding
text between its marker and the next; a missing field should default
gracefully (empty string / None), never abort the whole block.

### 2.3 Self-healing retry on truncation
If a chunk's API response has `stop_reason == "max_tokens"` (truncated
mid-response), split that chunk in half (at a paragraph boundary if
possible, else a sentence boundary, else a raw midpoint) and retry each half
recursively, up to depth 3. This handles unusually dense sections without
needing a perfect chunk-size guess up front.

### 2.4 Digest generation
Separate, second API call. Input: only the already-extracted new/changed
clauses (their text, impact, prevalence, rationale) — not the raw document
again. Ask for exactly two short paragraphs (plain prose, no markdown): (1)
what's genuinely worth reading carefully, especially anything both
high-impact and unusual; (2) reassurance about what's safe to skim, plus an
honest overall read on how the document compares to typical practice. If
nothing came back new, say so plainly rather than manufacturing urgency.
Explicitly instruct: informational triage, not legal advice; describe, don't decide for the user.

---

## 3. Rating semantics (do not conflate these two axes)

- **Impact** = "how much does this matter if it applies to me" — High /
  Medium / Low / Inconsequential / Undetermined Risk.
- **Prevalence** = "how much of a real choice do I have about this" —
  Standard / Unusual.

Priority sort = impact tier primary (High/Undetermined Risk highest, then
Medium, then Low/Inconsequential), Unusual-before-Standard as the tiebreaker
within a tier. A clause is eligible for the low-priority bulk-review cluster
**only if** `prevalence == "Standard"` AND `impact in ("Low", "Inconsequential")`.
Undetermined Risk and Unusual are never cluster-eligible, regardless of the
other axis.

---

## 4. UI / screens

Five views, same as the original:

1. **Baseline** — view (and manage, see §6) the control group, grouped by category.
2. **Submit** — paste text, pick category, optional source URL, scan.
3. **Review** — decisions happen here. Structure: needs-attention clauses
   (sorted by priority) → low-priority cluster (collapsed, explicit
   group-vs-individual choice, never a silent default) → already-dispositioned
   clauses (muted, out of the way) → matched-to-baseline clauses (hidden
   behind a clearly-labeled toggle, not buried in small text).
4. **Compare** — same underlying data and same accept/reject actions as
   Review, but organized for reading the whole document top-to-bottom
   (matched + new together, sorted by priority) without re-sorting as the
   user acts. A decision on either screen must be reflected on the other
   immediately (there is only one copy of the data — do not build two).
5. **Log** — full scan history; delete a scan record (impact-preview first:
   how many baseline entries it contributed, how many other documents'
   clauses matched against them, and an explicit statement that deleting
   the log record does not touch the baseline).

**UI requirements carried forward from hard lessons in the original build:**
- Every bulk or destructive action needs a real confirm step showing its
  impact *before* the action, not after.
- Significant actions (bulk-accept-all, reset-all-data) need visually
  distinct, clearly-labeled treatment — not placed where an incidental
  click is likely.
- Persistent context (which screen, which document) should stay visible
  even when scrolling a long list.
- Matched-clause and low-priority-cluster reveal controls should be
  visually prominent buttons, not small underlined text easy to miss.

---

## 5. Bulk clause disposition (the cluster)

Present group-vs-individual as an **explicit, equally-weighted choice** —
never assume group review is wanted by default, even though it's the
recommended option. If group is chosen, the clause list must be expanded
(fully shown) before a bulk-accept action becomes available — there is no
path to bulk-accepting content that was never displayed. If individual is
chosen, each clause gets full normal accept/reject treatment, just visually
tagged as having come from the low-priority pool.

---

## 6. Baseline entry management — the most important logic in the app

**Core principle, stated by the tool's owner and non-negotiable:** a
semantic match already constitutes a full, first-class acceptance — not a
provisional or lesser one. The fact that a clause was accepted quickly
*because* it resembled something already accepted does not make that
acceptance conditional on the original clause's continued existence.

**Baseline entries must never be implemented as foreign keys back to the
agreement that produced them.** They are independent snapshots (text +
citation string) from the moment they're created. This is what makes the
following behavior possible:

**When a baseline entry is removed:**
- **Default:** every clause elsewhere that had matched this entry becomes
  its own independent new baseline entry (deduplicated by exact text, each
  with its own proper source citation). **Nothing reverts to pending
  review.** This happens automatically for all matches, not as a
  one-at-a-time pick from a list — the acceptance decision was already made
  once, via the match.
- **Explicit opt-in alternative** ("remove entirely, discard matches too"):
  only for deliberately correcting a mistake. This path *does* revert
  affected clauses to new/pending, with an honest `Undetermined Risk`
  placeholder (never a guessed real rating) and a distinct flag/warning
  (`match_invalidated`) so it's visually clear *why* the clause reappeared,
  rather than looking like an ordinary first-time miss.

Always preview the impact (how many clauses, in which documents) before
either action executes.

---

## 7. Testing / validation checklist

Recreate these test cases to confirm equivalent behavior to the original:

- A clause that's a **near-exact rewording** of a baseline entry (different
  words, same meaning) should be flagged `matches_baseline`, not `new`.
- A clause that's **genuinely ambiguous** (vague standard, unclear
  consequence) should get `Undetermined Risk`, not a guessed rating.
- A **dense chunk** that would overflow the token budget should trigger the
  self-healing split-and-retry, not fail the whole scan.
- A single paragraph containing **multiple unrelated legal concepts**
  should be split into separate provisions, not treated as one.
- Removing a baseline entry with **exactly one** matching clause elsewhere
  should result in zero clauses needing re-review (the match is promoted
  automatically).
- Removing a baseline entry with **matches of differing exact wording**
  across multiple documents should promote all of them as separate entries
  (default path) — confirm none silently disappear.

---

## 8. What's explicitly out of scope for v1 of the Python rebuild
(carried forward from the original's known limitations — don't rebuild these
unless specifically asked)
- Automated/scheduled background re-scanning of a company's terms.
- A live database of "how common is this clause across the industry" —
  Prevalence remains a model judgment call.
- Cross-baseline-entry deduplication beyond exact-text matching.
