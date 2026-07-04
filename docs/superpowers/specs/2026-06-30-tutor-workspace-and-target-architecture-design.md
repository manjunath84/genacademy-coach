# Tutor Workspace + Full Target Architecture — Design

**Date:** 2026-06-30
**Status:** Draft for review
**Skill:** produced via `superpowers:brainstorming`; next step is `superpowers:writing-plans` for Phase A.

## 1. Purpose & dual mandate

This design does two things at once:

1. **Design the full target architecture** for the Adaptive GenAcademy AI Tutor & Q&A Coach — the
   already-shipped grounded core plus every deferred extension, each behind an explicit phase gate.
2. **Specify the first not-yet-built slice to build now:** the split-pane **Tutor Workspace**
   (conversational tutor pane + grounded companion context panel).

The slice serves a **dual mandate**: it is both the **3-minute breakout demo** and a **real product**
increment. We build ONE real slice that lands in the repo, reuses the shipped engine, and passes the
gates; the "demo" is that same slice run on a curated set of real Week-1 questions. No throwaway demo code.

## 2. Invariant spine (constant across every phase)

> **Agentic in teaching; deterministic in grounding, citations, filters, refusal, and privacy.**

- **Grounded-or-refuse.** Answers exist only when grounded in retrieved course evidence.
- **Deterministic refusal.** The `STOP / CONFIRM / PROCEED` confidence bands in `specs/tech-stack.md`
  govern behaviour; refusal is deterministic below `STOP`; refusal recall on negative controls = `1.000`
  is a release gate.
- **One source-prioritized retriever.** Citations captured at retrieval, role-keyed (`role → span_id`),
  never reconstructed after generation.
- **Agenticity in the open.** The agent chooses the teaching action among grounded options; the choice
  is shown in the trace (allow-listed cards).
- **Privacy.** No raw learner or corpus text, filenames, or private URLs in committed/shared artifacts;
  safe display labels only.

## 3. Current substrate (already shipped — reused, not rebuilt)

Teach loop, quiz, skill-gap diagnosis, session memory, escalation, privacy, trace, the full eval harness,
and the local Gradio app are shipped (roadmap: "past the teach-loop MVP"). Role-keyed provenance
(`role → span_id`) already exists. Phase A builds directly on this; it adds a projection + a view, not a
new engine.

## 4. Full target architecture — phased & gated

The spine (§2) is constant. Each phase is additive and gated. Ordering rationale: ship the **visible
differentiator** first, then the **substrate**, then progressively heavier / privacy-riskier layers —
with the consent- and data-heavy layers gated hardest and latest.

| Phase | Layer | Gate to enter |
|---|---|---|
| **A (build now)** | Split-pane Tutor Workspace — read-only provenance-projection panel + evidence card + per-lane sections + slide-visual card + deterministic next-step chips, current index, Gradio-native | Panel renders only cited spans; no second retrieval |
| **B** | Coach v2 Slice-0 corpus substrate — Week-1-only, notes-excluded, new `corpus_version` + recalibration, lane quotas, filter-aware refusal | Recalibration measured; refusal recall still `1.000` |
| **C** | Agentic panel upgrade — runtime source-switcher over *already-cited* lanes + agentic curation/phrasing of next-step chips, shown in trace | Switch never triggers a new answerability decision |
| **D** | Current-docs / web lookup — default-**OFF**, opt-in, quarantined lane, separately cited | External content never merges into the course corpus |
| **E** | Voice I/O — speech-to-text in, text answer first, optional audio playback (ElevenLabs TTS) | Text grounding reliable first |
| **F** | Consent-gated tutor voice cloning | 5-part gate: written consent · approved samples · in-app disclosure · deletion controls · opt-out |
| **G** | Admin ingestion / upload — controlled workflow + leak / eval-contamination checks before visibility | Uploaded material checked against the held-out eval set |
| **H** | Invite-code cohort access / auth | Standard auth review |
| **I** | Learner progress dashboard / cohort analytics — privacy-scoped, derived state only | No raw learner text; retention window + deletion; consent |

Quiz and skill-gap are already shipped; "mock-interview mode" is a later extension of the quiz layer,
folding in around C–I.

## 5. Phase A — Split-pane Tutor Workspace (the build slice)

### 5.1 Scope (approach A1)

Two-column Gradio workspace on the **current index**. Left: the existing chat (reused). Right: a
**read-only companion panel** that projects the current turn's cited spans and flips to a
refusal/escalation state when the turn is below `STOP`. No agentic switcher.
Includes (A2, confirmed in Phase 1): per-lane collapsible sections grouping cited spans by lane + a
one-line "why this source."
Includes (confirmed 2026-07-02): the **slide-visual card** — for slide-lane citations the panel shows
the stored page image of the exact cited slide (rendered from the deck via headless conversion at build
time; real asset, never generated). Citation → slide-index resolution happens deck-side — the pptx
loader already emits per-slide structure — so the **current index is untouched**. Slide images live in
a gitignored store and are served at runtime only; the repo is public, so they are never committed.
(Recorded exception, 2026-07-04: one inspected demo slide is published in the mockups at the owner's
direction; the runtime store stays gitignored.)
Includes (confirmed 2026-07-03): **deterministic next-step suggestion chips** (PRD FR-W10) — 2–4
anchor-validated chips per turn (continue / comprehension / practice; recovery set on refusal), built
from teach-loop state, corpus adjacency, near-miss retrievals, and session-memory dedupe. No new model
calls; clicking a chip submits a normal turn through the full pipeline. Chips are navigation, never
evidence, and never display span content. Design doc: `docs/coach-v2-next-step-suggestions.md`.

### 5.2 Rendering

`gr.Blocks`, two columns, **allow-listed Gradio components only** (Markdown / Accordion + status chips).
No custom HTML and no FastAPI/HTMX — both are explicitly deferred (`specs/tech-stack.md`,
`docs/production-roadmap.md`). MINT: this slice does not earn those layers.

### 5.3 Data contract (the one new interface)

The tutor turn emits a pure `PanelPayload`:

- `state ∈ { evidence, clarify, refusal }`
- `items: [ PanelItem { lane, source_label_safe, citation_id, role, confidence_band, extract_text, slide_image_ref? } ]`
  (`slide_image_ref` is optional — set only for slide-lane citations whose stored page image exists)
- `chips: [ SuggestionChip { kind: continue|comprehension|practice|recovery, label_safe, anchor, reason_code } ]`
  — emitted from the same turn state (adjacency = manifest lookup; near-misses = the turn's own
  retrieval pool; **no second retrieval**); a chip without a resolvable anchor is dropped.

Built in the **pure core** from the *same* retrieval / turn object (reusing `role → span_id`). It never
issues a new query. The panel is a pure render of this payload.

### 5.4 Panel decision policy

- below `STOP` / out-of-corpus → `refusal` (offer mentor escalation).
- ambiguous-but-in-corpus → `clarify` (**in-corpus only — never a refusal bypass**).
- `CONFIRM` / `PROCEED` → `evidence`: feature the primary teaching-role cited span; render other cited
  lanes as read-only sections.
- **Invariant:** no panel item without a `citation_id` already in the turn's citation set.

### 5.5 Module boundaries (isolation)

- `panel_payload.py` (pure core) — turn/provenance → `PanelPayload`. No Gradio import; unit-testable.
- `source_labels.py` (privacy) — span metadata → safe display label; no raw filename/path/URL.
- `slide_images.py` (assets) — deck → per-slide PNGs (headless render, refreshed per corpus version) +
  citation → slide-index resolver; the image store is gitignored.
- `suggestions.py` (pure core) — turn state → `SuggestionChip[]` (slot rules, anchor validation,
  memory dedupe, chip cap); no Gradio import; unit-testable.
- workspace wiring in `app.py` (thin view) — renders `PanelPayload`, swaps on `state`.
- Reused unchanged: retriever, grounding, `teach_agent`, provenance, trace, privacy.

### 5.6 Evals / tests (deterministic; golden files, scorer, and frozen `test` split untouched)

- panel-provenance-subset invariant (every panel `citation_id` ∈ the turn's citation set).
- no-second-retrieval assertion (payload derives from the same retrieval object).
- refusal-state renders escalation, not evidence.
- privacy-label test (no raw filename / path / URL in `source_label_safe`).
- pure-core test (payload builder imports no web framework).
- slide-image tests: `slide_image_ref` appears only on slide-lane items; the resolved file exists; the
  image store path is gitignored (never committed).
- chip tests: every chip anchor resolves (drop-if-not); suggested topics never deterministically refuse
  (dev split only); refusal state emits the recovery set; visited-topic dedupe; ≤4 chips; no raw
  filenames in labels.

### 5.7 Demo path (breakout)

Curate 2–3 real Week-1 questions that retrieve cleanly, plus one real out-of-corpus question that
refuses. **Real retrieval only — no fabricated answers.** The panel shows only safe labels + extractive
course excerpts (fine to display to the cohort's own material; nothing is committed). The phased map (§4)
and the spine (§2) are the pitch backbone; the deterministic refusal is the demo's money shot.

### 5.8 "Done" bar

In the Gradio UI: a Week-1 question shows answer + citations + the evidence card projecting the *exact*
cited spans; an out-of-corpus question flips the panel to refuse + escalate; tests green; `ruff` clean;
`git status` shows nothing changed under `corpus/`, `eval/`, or the golden set.

## 6. Non-goals / deferred (explicit)

Agentic switcher (C), corpus rework (B), web-lookup (D), voice (E/F), admin upload (G), auth (H),
analytics (I), generated/synthesized visuals (banned in every phase), custom HTML / FastAPI-HTMX.
(Real-asset slide page images are **in scope** — §5.1.)

## 7. Risks & mitigations (carried from prior adversarial reviews)

- Panel becomes a second retrieval that can disagree with the answer → data contract forbids it +
  no-second-retrieval test.
- "Clarify" erodes the deterministic refusal → clarify is in-corpus only; below-`STOP` always refuses.
- Synthesized / decorative panel content → extractive real-span only; no summaries or images.
- Raw filename leakage in labels → safe-label mapping + privacy test.
- Lane starvation (surfaces when B lands) → lane quotas / over-fetch in Phase B.
- Live demo failure → curated real demo path + tests green before presenting.

## 8. Resolved decisions (2026-06-30)

- A2 per-lane collapsible sections: **included in Phase A / Phase 1** (not deferred).
- Slide-visual card (added 2026-07-02): **included in Phase 1** — real stored slide images only,
  deck-side citation→slide resolution, no index changes, gitignored image store (the repo is public).
- Next-step suggestion chips (added 2026-07-03, Approach A): **deterministic version in Phase 1**,
  agentic curation in Phase C — anchor-validated, no new model calls, chips are never bypasses.
- Commit: this spec + the slice on a **branch off `main`**, committed on your approval.
- Build proceeds **phase-by-phase** per §4.
