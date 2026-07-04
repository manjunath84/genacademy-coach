# Next-Step Suggestion Chips (FR-W10) — Design

**Date:** 2026-07-03
**Status:** Approved (Approach A) — deterministic chips in Phase 1; agentic curation deferred to Phase C
**Feature id:** FR-W10 in `docs/coach-product-requirements.md`; build detail in
`docs/superpowers/specs/2026-06-30-tutor-workspace-and-target-architecture-design.md` §5
**Inspiration:** the common assistant pattern of post-turn suggestion chips (interaction shape only —
no third-party UI copied)

## 1. What it is

After each tutor turn, the workspace shows 2–4 clickable **next-step chips** under the reply — e.g.
"Next: *(next section title)*", "Re-explain differently", "Quiz me on this", "Show a handout exercise".
The system proposes the learner's next move based on what was just taught, how the learner did, and
where the current material sits in the course.

## 2. The one hard rule

> **Never suggest what you can't ground.** Every chip carries a grounding **anchor** — a span id, a
> deck/section adjacency reference, or a bounded teaching action — validated at creation time.
> No anchor → the chip is dropped. Clicking a chip submits a normal turn through the full pipeline
> (retrieval → confidence bands → refusal floor). **Chips are shortcuts, never bypasses.**
> **And the anchor survives the click:** the chip submits a structured payload (`chip_id`,
> `anchor_type`, `anchor_id`, `filter_scope`, `reason_code`) — never just its label text — and the
> receiving turn re-resolves the same anchor or drops the chip as stale. A chip can be invalidated;
> it can never degrade into a label-only query that self-refuses.

This kills the naive version's worst failure: the system suggesting a topic, the learner clicking it,
and the deterministic gate refusing the system's own suggestion — a self-inflicted refusal loop.

## 3. Where the intelligence comes from (no new model calls in Phase 1)

1. **Teach-loop state** (shipped) — check-question outcome + confidence band decide the pedagogical
   move: re-explain vs advance vs quiz.
2. **Corpus structure** — the cited span knows its place: deck/session order is the curriculum graph,
   so "next subtopic" is adjacency (next slide/section), not generation.
3. **Near-miss retrievals** — spans retrieved in *this turn's* query but not cited: semantically
   adjacent by construction, zero extra retrieval. Source for "related topic" chips.
4. **Session memory** (shipped) — visited topics deprioritized; struggled topics resurface as
   "revisit" chips. Personalization stays deterministic and privacy-scoped (derived state only).

Boundary: near-miss spans feed **chips only, never the evidence panel**. The panel remains proof of
*this* answer (projection of cited spans, FR-W2); chips are routes to the *next* turn and never display
span content — labels only.

## 4. Chip taxonomy — what shows when

2–4 chips, three slots, state-dependent:

| Turn state | Slot 1 — Continue path | Slot 2 — Comprehension | Slot 3 — Practice/Depth |
|---|---|---|---|
| **PROCEED + check passed** | "Next: → *(next slide/section title)*" | "Quiz me on this" | "Show a handout exercise" |
| **PROCEED + check failed/skipped** | "Re-explain differently" (lens switch) | "Break it into steps" | "Show me the slide again" |
| **CONFIRM** (partial evidence) | "Narrow it: ask about *(cited subtopic)*" | "Show exactly what the course says" | "Flag for mentor" |
| **STOP / refusal** | "Ask about *(nearest in-corpus topic)*" | "Browse Week-1 topics" | "Send to mentor" |

The refusal row is the differentiator: **refusal stops being a dead end** — the honest "I can't ground
this" now re-routes the learner into the corpus with anchored recovery chips.

## 5. Agentic vs deterministic (same spine as the rest of the system)

- **Deterministic (Phase 1):** candidate generation (adjacency, near-misses, teach state, memory
  dedupe), anchor validation, filter-scope compliance (candidates come only from within the learner's
  active filters — a chip never widens them), safe labels (reuse the source-label mapping), chip cap (≤4).
- **Agentic (Phase C):** choosing + phrasing the top chips from the validated candidate pool, logged in
  the trace (`suggested: [next-subtopic, quiz, exercise]`). Joins Phase C where "agent curates the
  workspace" already lives.
- Labels come from corpus headings/titles via the safe-label mapping — a chip can never promise content
  that isn't there, and never leaks raw filenames.

## 6. Approaches considered

- **A — deterministic Phase 1, agentic curation Phase C** (**chosen**): rule-based slot-filling; zero
  new model calls, zero egress, fully testable; demos identically to the "smart" version.
- **B — agentic from day one:** marginally smarter feel; +latency, +cost, +an eval surface Phase 1
  doesn't need. Rejected for now (MINT: earn the model call once rule-based chips measurably feel dumb).
- **C — defer entirely to Phase C:** cleanest scope but loses refusal-recovery UX and the demo moment;
  the deterministic version is cheap. Rejected.

## 7. Data contract

Emitted by the pure core alongside `PanelPayload`, from the **same turn state** (no second retrieval;
adjacency is a manifest lookup, near-misses come from the turn's own retrieval pool):

```
SuggestionChip {
  kind:        continue | comprehension | practice | recovery
  label_safe:  display text from corpus headings via safe-label mapping
  anchor:      span_id | slide_ref | action_id     # must resolve, or chip is dropped
  reason_code: e.g. next-in-deck, near-miss, check-failed, refusal-recovery
}
```

## 8. Tests / evals (deterministic; golden files and frozen `test` split untouched)

- every chip has a resolvable anchor (drop-if-not invariant);
- the click payload preserves the anchor (never a label-only submission); stale anchors drop the chip
  rather than refusing;
- chips respect the active filter scope; near-miss candidates outside the filter scope are excluded;
- a suggested topic chip, when submitted, does not deterministically refuse (validated on the dev split
  only);
- refusal state emits the recovery set, never topic chips without anchors;
- visited-topic dedupe against session memory;
- labels contain no raw filename / path / URL;
- chip count ≤ 4; pure-core builder imports no web framework.

## 9. Open items

- Mockup update (chips in the evidence + refusal screens) — **done 2026-07-03**, both states in
  `docs/assets/mockups/` (continue/comprehension/practice chips on evidence; recovery set on refusal).
- Chip-click telemetry as curriculum signal for the Phase-I progress dashboard (forward-compatible;
  log chip ids only, never raw learner text).
