# Agreement Scanner — Technical Documentation

Companion to the Quick Start Guide. This document explains *how* the tool
works internally — the logic, data model, and design decisions — for anyone
maintaining, extending, or rebuilding it. See `Agreement_Scanner_Architecture.mermaid`
for the visual workflow diagram.

---

## 1. Architecture overview

This is a single-file React application, running as a Claude artifact:

- **UI:** React with inline styles, no external component library.
- **AI calls:** made directly from the browser to `https://api.anthropic.com/v1/messages`,
  using the Claude Sonnet 4.6 model, billed through the artifact's own usage
  allowance (no separate API key).
- **Persistence:** the artifact's `window.storage` key-value API — three keys:
  `baseline-data`, `agreements-data`, `review-log-data`. Each holds a
  JSON-serialized snapshot of its respective data structure.
- **No backend, no database, no server.** Everything runs client-side in the
  browser tab.

---

## 2. Data model

### Agreement (one per scanned document)
```
{
  id, name, sourceUrl, category, dateSubmitted, dateReviewed,
  status: "pending review" | "reviewed",
  baselineSizeAtSubmission: number,   // how many baseline entries existed
                                       // in this category at scan time —
                                       // used to distinguish a real
                                       // comparison from a baseline-seeding
                                       // scan (where this is 0)
  digest: string | null,              // AI-written 2-paragraph summary
  clauses: [Clause, ...]
}
```

### Clause (one per extracted provision)
```
{
  id, ref,                            // e.g. "§7"
  text,                               // verbatim extracted text
  matchStatus: "new" | "matches baseline",
  impactRating: "High"|"Medium"|"Low"|"Inconsequential"|"Undetermined Risk"|null,
  prevalence: "Standard"|"Unusual"|null,
  matchedEntryText: string | null,    // snapshot of the baseline text it matched
  rationale, prevalenceRationale,     // one-sentence AI explanations
  confidence: number|null,            // 0–1
  disposition: "pending"|"accepted"|"rejected",
  dispositionDate,
  aiFailed: boolean,                  // true if this came from the offline fallback
  matchInvalidated: boolean           // true if this clause's match was later
                                       // invalidated by baseline entry removal
}
```
`impactRating` and `prevalence` are only ever populated when `matchStatus === "new"`.
Matched clauses carry `null` for both — they were never independently rated,
because rating is skipped precisely because something judged equivalent
already exists.

### Baseline Entry (one per accepted clause, grouped by category)
```
{ id, text, source, dateAdded }
```
`source` is a human-readable citation string (e.g. `"Basecamp — Terms of
Service (https://...)"`), not a reference to any Agreement record. **This is
the single most important design decision in the whole app**: baseline
entries are independent, self-contained snapshots. Nothing about them
depends on the Agreement record that produced them still existing.

### Review Log Entry (one per scan, for history)
```
{ id, agreementId, name, sourceUrl, dateReviewed, newFound, accepted, rejected, pending }
```

---

## 3. The core workflow

1. **Submit** — user pastes raw text, picks a category, optionally a source URL.
2. **Chunking** — the raw text is split into ~2000-character sections at
   paragraph boundaries (`chunkRawText`). This exists because a single API
   call asking the model to both segment *and* verbatim-echo a full document
   back can exceed the response token budget.
3. **Per-chunk AI call** (`aiSegmentCompareAndRateChunk`) — one call per
   chunk. The model is given the chunk's raw text and the current category
   baseline, and asked to:
   - Segment the chunk into discrete legal provisions (not sentence-level,
     not whole-paragraph-level — see §4).
   - For each provision, decide `matches_baseline` or `new`.
   - For `new` provisions: assign Impact and Prevalence ratings (see §5),
     a one-sentence rationale for each, and a confidence score.
4. **Self-healing retry** (`aiSegmentCompareAndRateChunkWithRetry`) — if a
   chunk's response is truncated (`stop_reason: max_tokens`), the chunk is
   split in half and each half is retried recursively (max depth 3), rather
   than failing the whole scan.
5. **Digest generation** (`generateDigest`) — a second, separate AI call,
   given only the already-extracted new/changed clauses (not the raw
   document again), asked to write a 2-paragraph plain-language summary of
   what deserves attention vs. what's safe to skim.
6. **Review / Compare** — the human decision layer (see §6, §7).
7. **Accept → Baseline Entry created.** **Not Accepted → logged, excluded.**

---

## 4. Why the AI output format is delimited text, not JSON

Early versions asked the model to return a JSON array. This failed
repeatedly in practice: real legal text contains quote marks (`"Company"`,
`"Services"`), and the model would produce a literal `"` inside a JSON
string value without escaping it, breaking `JSON.parse` outright — often
many characters into a large response, discarding everything.

The fix: the model instead outputs plain-text blocks delimited by unique
sentinel markers:
```
<<<PROVISION>>>
<<<TEXT>>>
...verbatim text, quotes and all, no escaping needed...
<<<MATCH_STATUS>>>
NEW
<<<MATCHED_BASELINE_ID>>>
NONE
<<<IMPACT_RATING>>>
High
<<<PREVALENCE>>>
Unusual
<<<RATIONALE>>>
...
<<<PREVALENCE_RATIONALE>>>
...
<<<CONFIDENCE>>>
0.85
<<<END_PROVISION>>>
```
The parser (`parseDelimitedResponse`) is deliberately **lenient**: it splits
on `<<<PROVISION>>>`, and any block missing a field just gets `null`/empty
for that field rather than discarding the whole block. A single malformed
provision no longer invalidates every provision around it — a major
robustness improvement over strict JSON parsing.

---

## 5. Impact vs. Prevalence — two independent axes

- **Impact**: *"How much does this matter if it applies to me?"* — High,
  Medium, Low, Inconsequential, or Undetermined Risk (used only when the
  language is genuinely vague, not as a default for anything merely unfavorable).
- **Prevalence**: *"How much of a real choice do I have about this?"* —
  Standard (common industry-wide, even if unfavorable) or Unusual (goes
  beyond typical practice).

These are judged independently and combined for prioritization
(`clausePriorityScore`): impact tier is primary, prevalence is the
tiebreaker within a tier (Unusual sorts above Standard at the same impact
level). A mandatory-arbitration clause is typically **High + Standard**
("know about it, don't agonize"); a broad AI-training content license is
**High + Unusual** ("this is the one to actually read").

Prevalence is judged from the model's general training on how these
documents typically read — **not** a live database of current ToS
documents, and explicitly not judged against the user's own (possibly tiny)
baseline, since that would conflate "not in my baseline yet" with "unusual
industry-wide."

---

## 6. Clustering logic (Review screen)

A clause is cluster-eligible (`isLowPriorityClause`) only if **both**:
`prevalence === "Standard"` **and** `impactRating` is `"Low"` or
`"Inconsequential"`. Undetermined Risk is *never* eligible (ambiguity is
itself a reason for individual attention), and Unusual is never eligible
regardless of impact (that's precisely the signal meant to interrupt the user).

The cluster presents an explicit, equally-weighted choice — **"As a group
(recommended)"** or **"Individually"** — never a silent default. Choosing
group review still requires expanding the panel (seeing every clause in it)
before the bulk-accept button becomes available; there is no path to
bulk-accepting content that was never shown.

---

## 7. Review vs. Compare

Both screens read and write the same underlying `agreements` array — there
is no data duplication and no sync step, because there's only one copy of
each clause object. The difference is purely organizational:

- **Review**: optimized for triaging a large fresh scan. Needs-attention
  clauses sorted to the top, the low-priority cluster collapsed, already-
  decided clauses moved out of the way at the bottom.
- **Compare**: optimized for reading the whole document top-to-bottom in one
  pass, matched and new together, without re-sorting as you act on things.

Both support the same Accept/Not Accept actions; a decision made on either
screen is immediately reflected on the other.

---

## 8. Baseline entry removal and the "match = acceptance" principle

This was the single most-revised piece of logic in the whole build, based
directly on the tool owner's explicit judgment call, so it's worth recording
precisely:

**A semantic match is treated as a full, first-class acceptance** — not a
lesser tier of it. The fact that a clause was accepted *quickly, because it
resembled something already accepted*, does not make that acceptance
provisional or dependent on the original clause continuing to exist.

Consequently, when a baseline entry is removed
(`handleRemoveBaselineEntry`):

- **Default behavior:** every clause elsewhere that had matched the removed
  entry becomes **its own independent baseline entry** (deduplicated by
  exact text), with its own proper source citation. Nothing reverts to
  pending review. This is automatic, not a per-clause choice — the user
  already made the acceptance decision once, via the match.
- **Explicit opt-in alternative** ("Remove entirely, discard matches too"):
  for the genuinely different case of correcting an actual mistake — this
  path *does* revert affected clauses to `new`, `pending`, with an honest
  `Undetermined Risk` placeholder (since they were never independently
  scored) and a `matchInvalidated: true` flag that surfaces a distinct
  warning message in the UI, rather than looking like an ordinary
  first-time miss.

The impact of either choice is always shown *before* the user acts — how
many clauses, in which documents, would be affected — never applied silently.

---

## 9. Integrity principles enforced throughout

These aren't features so much as constraints the whole design operates
under, established over the course of development:

1. **Nothing gets accepted without being shown to the user first**, even in
   bulk — a group summary counts as "shown," a silent auto-classification does not.
2. **Bulk actions require a real confirmation step** (`window.confirm` does
   not work reliably inside the artifact sandbox — every confirm flow in
   this app is a hand-built two-step, arm-then-confirm UI pattern instead).
3. **Destructive or structural actions show their impact before acting** —
   deleting a scan record or removing a baseline entry always previews what
   depends on it first.
4. **Fallbacks are honest, not confident-looking.** When AI comparison fails
   outright, clauses get `Undetermined Risk` and a visible `aiFailed` flag —
   never a guessed rating presented as real.

---

## 10. Known limitations

- **No document chunking size guarantee for extremely long documents** —
  the self-healing retry handles most density problems, but there's no
  hard ceiling on how many API calls a single very long document could
  trigger.
- **No automated/scheduled re-checking** — the tool only runs while the
  artifact tab is open; it cannot periodically re-scan a company's terms in
  the background.
- **Prevalence judgment is a model estimate**, not a benchmarked fact — see §5.
- **Matching is exact-text-based for baseline-removal bookkeeping**
  (`matchedEntryText === entry.text`) — if the same conceptual clause exists
  in the baseline with two different exact-text entries, removal logic
  treats them as unrelated.
