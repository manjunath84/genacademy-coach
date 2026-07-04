# Tutor Workspace — Session Context & Decision Log

**Date range:** 2026-06-30 → 2026-07-03
**Purpose:** durable context for the design sessions that produced the finalized PRD, the target
architecture spec, the workspace mockups, and features FR-W9/FR-W10 — so any future session (or a
second-model reviewer) can pick up without re-deriving the reasoning.

## 1. How we got here (decision timeline)

1. **Breakout draft review.** A private draft proposal (adaptive AI tutor over course material) got a
   five-role panel review: verdict *approve with changes*. Top risks: comprehension grading presented
   as easy (it's the most-deferred capability), learner-profile privacy, agent-action vs deterministic
   pipeline conflation, web-lookup default-on, unnamed retrieval mechanism.
2. **Scope decision.** Owner chose to design the **full target architecture** (core + every deferred
   extension) *and* build a prototype. Brownfield reality check: the grounded engine (teach loop, quiz,
   skill-gap, memory, escalation, privacy, trace, eval harness, Gradio app) is already shipped — so the
   buildable prototype targets the not-yet-built **split-pane Tutor Workspace**.
3. **Expert calls (owner delegated):** run on the **current shipped index** (corpus rework stays
   Phase B); **Gradio-native** rendering (custom HTML / FastAPI-HTMX stay deferred); panel is a
   **read-only provenance projection** — renders only spans already cited by the turn, no second
   retrieval (the load-bearing invariant from the prior workspace review).
4. **Dual mandate.** The slice serves the 3-minute breakout demo *and* the real product — one real
   slice, demo = the slice on curated real questions. No throwaway demo code.
5. **Requirements-first pivot.** Owner asked to finalize product requirements and visualize the UI
   before any build ("design prototype" = PRD + mockups, not code). Delivered.
6. **Phase 1 scope confirmations:** per-lane collapsible sections (A2) — in; phased build (A→I) — yes;
   commit on a branch off `main` upon approval — yes.
7. **FR-W9 slide-visual card.** Owner: "RAG should pull the slide and show it on the right."
   Requirement added: for slide-lane citations the panel shows the **stored page image of the exact
   cited slide** — real asset rendered from the deck, never generated. Feasibility spike ran against
   the real Week-1 Session-2 deck: headless convert → 32 per-slide PNGs, keyed by slide index, stored
   gitignored. No re-index needed (deck-side citation→slide resolution).
8. **Privacy boundary exercised.** The repo is **public**; corpus and rendered slide images are
   gitignored. A pasted internal-enterprise screenshot was **declined for public embedding** (internal
   URL/hostname/username); instead a **private real-slide mockup variant** was produced under
   gitignored local docs for cohort demo use, while the committed mockups keep synthetic stand-ins.
   Standing rule: reference screenshots are inspiration-only; real corpus assets are runtime-only.
9. **Trace-line explainer.** The strip `action · lens · decision · cited spans` documented as the UI
   expression of the spine: action + lens are the agent's (logged) choices; decision band + cited
   spans are the system's deterministic measurements.
10a. **Real demo slide published (owner's direction, 2026-07-04).** The mockup's slide card first used
    an original synthetic infographic; the owner directed embedding a real slide. One inspected, benign
    slide (Week 1 · Session 2 · slide 22 — a framework-primitives overview; no personal data or internal
    systems) is published in `docs/assets/mockups/` as the featured asset. The remaining deck renders
    stay private (uninspected third-party content). FR-W9 wording amended to record the exception.
11. **FR-W10 next-step suggestion chips.** Owner requested intelligent "what next" suggestions
    (pattern: post-turn suggestion chips). Brainstormed; **Approach A approved** — deterministic,
    anchor-validated chips in Phase 1 (teach-state + corpus adjacency + near-miss retrievals + session
    memory), agentic curation in Phase C. Hard rule: never suggest what you can't ground; chips are
    shortcuts, never bypasses. Full design: `docs/coach-v2-next-step-suggestions.md`.

## 2. Artifact map

| Artifact | Path | State (2026-07-03) |
|---|---|---|
| Finalized PRD | `docs/coach-product-requirements.md` | in PR #61 |
| Target-architecture spec (phases A→I + Phase-A build detail) | `docs/superpowers/specs/2026-06-30-tutor-workspace-and-target-architecture-design.md` | in PR #61 |
| Suggestion-chips design (FR-W10) | `docs/coach-v2-next-step-suggestions.md` | in PR #61 |
| Public mockups (evidence + refusal, synthetic content) | `docs/assets/mockups/` | in PR #61; FR-W10 chips visualized in both states |
| Private real-slide variant + rendered deck pages | gitignored local docs | local-only, never committed |
| This context log | `docs/coach-v2-workspace-session-context.md` | in PR #61 |

## 3. Guardrails that shaped every decision

- Grounded-or-refuse; deterministic bands (`STOP/CONFIRM/PROCEED`); refusal recall `1.000` as release
  gate; frozen `test` split untouched.
- One retrieval per turn; the panel is a projection of its citations; citations captured at retrieval,
  role-keyed, never reconstructed.
- Extractive/real-asset only — generated visuals/summaries banned in every phase.
- Public repo ⇒ corpus content, slide images, internal screenshots, raw filenames never committed;
  safe display labels only.
- Gates: no code before an approved plan; builder ≠ reviewer; evidence before "done".

## 4. Loose ends

- **PR #61 open:** the design package on `docs/tutor-workspace-design-package` (PRD + spec + designs
  + mockups, FR-W10 chips included); merge pending owner review.
- **PR #58** (docs-only, pre-dates this thread) still open with one unaddressed finding (roadmap
  cut-order vs AD-13 framing); owner decision pending.
- **Next workflow step after commit:** `writing-plans` for Phase 1, then build (first plan task:
  productionize the already-spiked deck→slide-image pipeline + panel data contract).
