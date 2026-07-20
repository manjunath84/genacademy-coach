# Adaptive GenAcademy AI Tutor & Q&A Coach — Product Requirements (Finalized)

**Date:** 2026-06-30
**Status:** Finalized draft for review
**Consolidates:** the breakout project draft, the Coach v2 Week-1 PRD, the target-architecture design
(`docs/superpowers/specs/2026-06-30-tutor-workspace-and-target-architecture-design.md`), and the Tutor
Workspace review.
**Companions:** architecture / HOW → the design spec above · UI mockups → `docs/assets/mockups/`
(produced alongside this doc for visual review before build).

## 1. Summary

A grounded AI tutor over the actual GenAcademy course corpus (slides, session transcripts, handouts,
Q&A). It answers only from retrieved course evidence, shows the exact source beside every answer, and
refuses + routes to a mentor when it cannot ground an answer. **Agentic in how it teaches; deterministic
in grounding.**

**Dual mandate:** the near-term build serves both a 3-minute breakout demo and a real product increment
— one real slice, no throwaway demo code.

## 2. Problem & audience

- **Problem:** learners re-open slides, transcripts, handouts, and chat separately to understand one
  concept. No single grounded place explains a topic *and* shows where it came from.
- **Audience:** technically capable but not-yet-AI-fluent cohort members. Builder examples over academic
  ones; AI terms kept and defined in-line.
- **Teaching lenses (not identities):** low-code/no-code · code-heavy · bridge. Same grounded engine,
  different explanation style.

## 3. Product principles (non-negotiable spine)

- **P1 Grounded-or-refuse.** Answers exist only when grounded in retrieved course evidence.
- **P2 Deterministic grounding.** Confidence bands (`STOP/CONFIRM/PROCEED`, `specs/tech-stack.md`) govern
  behaviour; refusal deterministic below `STOP`; refusal recall on negative controls = `1.000` is a
  release gate (`AD-10`).
- **P3 One source-prioritized retriever.** Slides/handouts preferred, notes fill gaps, transcripts
  support; citations captured at retrieval, role-keyed, never reconstructed (`AD-4`).
- **P4 Agenticity in the open.** The agent chooses the teaching action among grounded options; the choice
  appears in the trace (`AD-7`).
- **P5 Honesty & privacy.** No fabricated content or numbers; no raw learner/corpus text, filenames, or
  private URLs in committed/shared artifacts; safe display labels only.

## 4. Baseline — already shipped (requirements below are additive)

Teach loop, quiz, skill-gap diagnosis, session memory, escalation, privacy, trace, the eval harness, and
the local Gradio app are shipped. Role-keyed provenance (`role → span_id`) exists.

## 5. Functional requirements

### 5.1 Grounded Q&A & tutor (shipped — restated)

- **FR-1** Answer a course question with a grounded explanation + citations, or refuse.
- **FR-2** Choose a teaching action (answer / step-by-step / clarify / quiz / re-explain / refuse+escalate);
  the action is shown in the trace.
- **FR-3** Apply the selected teaching lens.
- **FR-4** Refuse + offer mentor escalation when evidence is below `STOP` / out of corpus.

### 5.2 Tutor Workspace — split-pane (Phase 1, primary)

- **FR-W1** Two-pane workspace: conversational tutor (left) + grounded companion context panel (right).
- **FR-W2** The panel is a **projection of the current turn's retrieval** — it renders only spans already
  in that turn's citation map. **No second retrieval / answerability decision.**
- **FR-W3** Panel states: `evidence` (cited spans) · `clarify` (in-corpus disambiguation only) · `refusal`
  (escalation offer). Below-`STOP` → `refusal`; clarify never bypasses refusal.
- **FR-W4** Each panel item shows: safe source label · lane · citation id · confidence posture (status,
  not a control) · extractive span text.
- **FR-W5** **Per-lane collapsible sections** grouping cited spans by lane (slides / transcript / handout /
  Q&A), each with a one-line "why this source." *(Confirmed in Phase 1.)* **Lane display names speak
  learner-language, not corpus taxonomy:** `transcript` renders as "Instructor explanation", `qa` as
  "Cohort Q&A"; the artifact type (e.g., "live-session transcript") stays in the source card's
  provenance row. Internal lane ids in contracts and traces are unchanged. The "why this source" lines
  are deterministic per-lane templates written in tutor voice (e.g., slides → "the concept as presented
  in class", transcript → "how the instructor explained it live").
- **FR-W6** Read-only & extractive — no synthesized summaries or visuals, no decorative content from
  priors. Real stored assets are allowed (FR-W9); generated ones are banned in every phase.
- **FR-W7** A short grounded check question after tutoring (reuses the shipped check/quiz path).
- **FR-W8** Source labels are privacy-safe — decoupled from raw filenames / paths / URLs.
- **FR-W9** Slide-visual card: when a cited span comes from a slide deck, the panel shows the **stored
  page image of that exact slide** (rendered from the deck at build time — real asset, never generated),
  keyed citation → deck + slide index. Slide images live in a private, gitignored store and are served
  at runtime only; they are never committed — the repo is public. *Narrow public-demo exception,
  owner-approved and reaffirmed 2026-07-18: one inspected course slide (Week 1 · Session 2 · slide 22)
  may remain committed as the sole course visual in the evidence mockup and pitch storyboard. The
  mockup and storyboard's transcript and handout evidence remains synthetic; the exception does not
  cover other course assets.*
- **FR-W10** Next-step suggestion chips: after each tutor turn, 2–4 clickable suggestions (continue /
  comprehension / practice slots; a recovery set on refusal). **Every chip carries a grounding anchor**
  (span id, deck/section adjacency, or bounded teaching action) validated at creation — no anchor, no
  chip. Labels come from corpus headings via the safe-label mapping. Clicking submits a normal turn
  through the full pipeline (never a bypass). Chips are navigation, not evidence — they never display
  span content and are distinct from the panel's provenance projection. Phase 1 = deterministic
  candidate generation (teach-loop state · corpus adjacency · near-miss retrievals · session-memory
  dedupe); agentic curation/phrasing deferred to Phase C. Design: `docs/coach-v2-next-step-suggestions.md`.
  **Click contract:** a chip click submits a structured payload (`chip_id`, `anchor_type`, `anchor_id`,
  `filter_scope`, `reason_code`) — never just the label text; the next turn re-resolves the same anchor
  or drops the chip as stale (invalidation, never a refusal bypass). Candidates are generated within the
  learner's active filter scope — a chip never widens filters; `action_id` chips come only from the
  enumerated teaching-action menu, so non-content actions cannot promise grounded content.
- **FR-W11** Learner-first observability: the per-turn reasoning strip (action · lens · decision band ·
  citation count · chip ids) is **not** part of the default learner view — it reads as debug output to
  a non-technical learner. It is always captured in the local trace (allow-listed fields only) and is
  exposed in the UI only behind a collapsed "behind this answer" disclosure, plus a presenter/demo
  toggle for walkthroughs. The always-visible learner-facing status is the panel's plain-language
  grounding posture (FR-W4).

### 5.3 Retrieval, citations, filters

- **FR-R1** Metadata-tagged corpus: week · session · source-type · content-kind · topic · corpus-version ·
  citation-id.
- **FR-R2** Lane balance so no single source dominates (lane quotas / over-fetch — enters with the Phase B
  corpus substrate).
- **FR-R3** Optional strict filters (source-type / week / session); default = all approved sources.
- **FR-R4** Filter-aware refusal: filter empties evidence → "no evidence under this filter, broaden?";
  corpus empties (below `STOP`) → refuse + escalate. Never silently widen a filter.

### 5.4 Deferred capabilities (forward requirements — phased & gated)

Each is a real requirement for the target product, gated per the phase map (§7): voice I/O ·
consent-gated tutor voice cloning · default-OFF quarantined web-lookup · admin ingestion / upload ·
invite-code cohort access / auth · learner progress analytics · mock-interview mode.

## 6. Non-functional requirements

- **NFR-1 Privacy/security:** private corpus storage; no raw learner questions in committed logs; safe
  traces (allow-listed metadata only); mentor escalation carries minimum context.
- **NFR-2 Accessibility:** keyboard-navigable two-pane; panel state announced; confidence posture not
  conveyed by colour alone.
- **NFR-3 Performance (design bars — fill from dashboard, do not invent):** turn p95 latency ≤ target;
  cost/run no-regression.
- **NFR-4 Observability & evals:** retrieval recall@k · citation-faithfulness F1 (floor / aspirational) ·
  refusal recall = `1.000` (gate) · filter correctness · latency · cost. Frozen `test` split never used
  pre-final (`AD-12`, gate #4).
- **NFR-5 Rendering:** Gradio-native, allow-listed components; custom HTML / FastAPI-HTMX deferred
  (`specs/tech-stack.md`).

## 7. Scope & phasing (build proceeds phase-by-phase)

| Phase | Layer | Gate to enter |
|---|---|---|
| **1 / A (build now)** | Split-pane Tutor Workspace — read-only provenance-projection panel + evidence card **+ per-lane collapsible sections + slide-visual card (FR-W9) + deterministic next-step chips (FR-W10)**, current index (no re-index; citation→slide resolved deck-side), Gradio-native | Panel renders only cited spans; no second retrieval |
| **B** | Coach v2 Slice-0 corpus substrate — Week-1-only, notes-excluded, new `corpus_version` + recalibration, lane quotas, filter-aware refusal | Recalibration measured; refusal recall still `1.000` |
| **C** | Agentic panel upgrade — runtime source-switcher over *already-cited* lanes + agentic curation/phrasing of next-step chips (FR-W10), shown in trace | Switch never triggers a new answerability decision |
| **D** | Current-docs / web lookup — default-**OFF**, opt-in, quarantined lane, separately cited | External content never merges into the course corpus |
| **E** | Voice I/O — speech-to-text in, text answer first, optional audio playback | Text grounding reliable first |
| **F** | Consent-gated tutor voice cloning | 5-part gate: consent · approved samples · disclosure · deletion · opt-out |
| **G** | Admin ingestion / upload | Uploaded material checked against the held-out eval set |
| **H** | Invite-code cohort access / auth | Standard auth review |
| **I** | Learner progress dashboard / analytics — privacy-scoped, derived state only | No raw learner text; retention + deletion; consent |

Immediate build = **Phase 1 (A)**. Everything in §5.4 is out-of-scope for Phase 1.

## 8. Acceptance criteria — Phase 1 (Tutor Workspace)

- **AC-1** In the Gradio UI, a Week-1 question shows answer + citations + the evidence card projecting the
  exact cited spans, grouped by lane (collapsible).
- **AC-2** An out-of-corpus question flips the panel to refuse + escalate (no evidence shown).
- **AC-3** Panel-provenance-subset invariant holds (every panel citation ∈ the turn's citation set); no
  second retrieval.
- **AC-4** Source labels contain no raw filename / path / URL.
- **AC-5** Tests green; `ruff` clean; nothing changed under `corpus/`, `eval/`, or the golden set.
- **AC-6** Next-step chips render (≤4) with resolvable anchors in the evidence state; the refusal state
  shows the recovery set; a suggested topic chip, when clicked, does not deterministically refuse
  (validated on the dev split); chip labels contain no raw filename / path / URL; click payloads
  preserve the anchor (no label-only submission) and chips respect the active filter scope.
- **AC-7** The default render hides the reasoning strip (FR-W11); the "behind this answer" disclosure /
  demo toggle reveals allow-listed fields only; the panel's grounding-posture chip remains always visible.

## 9. Success metrics

The eval framework in NFR-4, with current values pulled from the dashboard (no invented numbers here).
Deterministic refusal and citation-faithfulness are the load-bearing signals.

## 10. Risks

- Panel becomes a second retrieval that can disagree with the answer → data contract + no-second-retrieval
  test.
- "Clarify" erodes the deterministic refusal → in-corpus only; below-`STOP` always refuses.
- Synthesized / decorative panel content → extractive real-span only.
- Raw filename leakage in labels → safe-label mapping + privacy test.
- Lane starvation (surfaces with Phase B) → lane quotas / over-fetch.
- The system suggests a topic it then refuses (self-inflicted refusal loop) → anchor-validated chip
  candidates only + the suggested-topic no-refusal test (AC-6).

## 11. UI direction & mockups

The panel decision policy (FR-W2 / W3 / W4 / W5 / W9 / W10) is the UI's backbone. Static mockups under
`docs/assets/mockups/` visualize the `evidence` and `refusal` states for review before build. The
conversation text is representative (not real corpus); the evidence mockup's slide card features the
one approved real slide recorded as FR-W9's exception (image, extracted span text, and alt text all
covered by it). At runtime, cited slides are served privately from the gitignored store. The real build
is Gradio-native and may differ cosmetically.
