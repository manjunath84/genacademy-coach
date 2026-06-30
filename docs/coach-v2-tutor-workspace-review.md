# GenAcademy Coach V2 — Tutor Workspace UI Adversarial Review

> **Context.** Pre-implementation design/product review of a proposed **Tutor Workspace** UI direction
> for Coach v2: a conversational tutor pane beside a grounded companion **context pane** driven by the
> same agentic RAG flow. This is gate #2 of `ai-dev-workflow` applied *before code* — a verdict +
> severity-ranked findings + the smallest safe UI scope. It is **not** an implementation plan and adds
> no code.
> **Panel lenses:** Learning Product UX · RAG Architect · Agentic Systems · Frontend/Product Eng ·
> Evaluation Eng · Accessibility · Privacy/Data Governance · Copyright/Brand-safety.
> **Grounding.** Repo read 2026-06-30 against the merged v2 PRD (`docs/coach-v2-week1-prd.md`) and both
> prior reviews. The PRD currently carries an **uncommitted working-tree draft** of a
> "Tutor Workspace UI Direction" subsection plus a new Slice-0 outcome; this review treats that draft as
> the proposal under review, not as settled.
> **Privacy-clean.** No raw course content, learner data, private URLs, secrets, partner names, raw
> corpus filenames, or the reference screenshots. The external AI-tutor screenshots are private,
> gitignored inspiration only; this review neither reproduces nor names the source product.

---

## Final verdict

**APPROVE THE DIRECTION — WITH CHANGES. Confidence: high.**

A grounded tutor-plus-context workspace is a genuinely good fit for this product and, done correctly,
*strengthens* the "grounded or refuse" brand instead of threatening it — but only under one architectural
constraint and one scope correction:

1. **The context pane must be a projection of the same single retrieval that grounded the tutor turn —
   never a second, independent retrieval/generation.** As drafted ("the agent should decide at runtime
   whether the right side should show a slide / handout / transcript / Q&A …") it reads like a second
   answerability decision that can disagree with the tutor pane. That is the core risk and the main
   change required.
2. **The full agentic, switchable, image-capable panel does not belong in Slice 0.** The PRD's
   working-tree draft folds it into Slice 0 (new outcome #8). Slice 0 already carries notes-exclusion + a
   new `corpus_version` + recalibration + lane-quota selection + per-lane citations + filter-aware refusal
   — each a real risk both prior reviews flagged. Stacking a new runtime-decision UI surface on top fights
   the project's load-bearing guardrail *"do NOT add new modes/surfaces ahead of the grounded core — earn
   each layer"* (`AGENTS.md:126-129`). Split it (Recommended Slice 0 below).

So: approve the workspace as the v2 product vision; keep Slice 0 the retrieval/grounding substrate plus
the **data contract** for a panel (and at most a minimal read-only evidence card); make the agentic
context pane its own next, separately-reviewed UI slice with its own evals.

---

## What is strong about the direction

- **It externalizes grounding instead of hiding it.** A pane that shows *the cited span the tutor
  actually used* turns the project's strongest property (citations captured at retrieval,
  `AGENTS.md:66-68`) into the primary UI affordance. For a not-yet-AI-fluent audience
  (`specs/mission.md:33-34`), "here is the slide/handout this came from" is more trust-building than a
  citation marker buried in prose.
- **Most of the "agentic decision" already exists deterministically.** Source priority
  (`AD-4`, `tech-stack.md:101-114`) and role-keyed provenance (the merged `teaching`/`check`/`final`
  provenance map) already pick the primary teaching span. The panel is largely a *render of an existing
  decision*, not a new one — low new surface area if scoped that way.
- **The refusal/clarify instinct is correct.** Asking a clarifying question on ambiguity rather than
  bluffing is exactly the brand — provided it never becomes a refusal bypass (see Blocking #2).
- **The "evidence-bound, no decorative content from priors" rule is stated up front** in the draft. That
  is the right north star; this review mostly hardens it into testable constraints.
- **Staging instinct is present** (text-first, no voice/web/upload in Slice 0), consistent with both
  prior reviews.

---

## Blocking issues (must resolve before this becomes a Slice 0 plan)

**B1 — The context pane must not be a second retrieval/answerability decision.** One grounded retrieval
per turn produces one evidence set and one provenance map; the tutor pane and the context pane are two
**renderings of that same set**. If the panel runs its own query or its own generation, it can show a
confident slide while the tutor refuses (or cite a span the tutor never used), which directly breaks
"answerability is evidence-bound" (`AGENTS.md:53-59`) and "citations captured at retrieval, never
reconstructed" (`AGENTS.md:66-68`). **Fix:** the panel renders only spans present in the current turn's
provenance map; no panel content without a `citation_id` the tutor turn already carries.

**B2 — "Clarify when retrieval is weak" must not erode the deterministic STOP refusal.** Below STOP or
with no citeable span, refusal is deterministic and non-overridable (`AGENTS.md:53-59`, `AD-10`,
`AD-13`). A clarifying question that fishes for a rephrase to coax a weak match is a refusal bypass.
**Fix:** clarifying questions are only for **ambiguous-but-in-corpus** cases (underspecified query,
multiple distinct in-corpus topics, or a CONFIRM-band item a narrower query would resolve). Out-of-corpus
/ below-STOP → refuse + escalate, never "clarify."

**B3 — "Slide-derived visual context" and "summary card" must be extractive/real-asset, never
synthesized from priors.** A generated diagram or a generated summary is a new generation with its own
hallucination surface. **Fix:** the panel may show a *real retrieved* slide asset or an *extracted* span
excerpt only. If any summary text is shown, it is a generation that must pass the same grounding check as
the tutor answer (`answer_grounded_in_spans`) and carry its own citation — otherwise show the extract,
not a summary. No invented visuals. (Real slide-**image** rendering is multimodal and is deferred — see
Deferred scope.)

**B4 — Source labels must be privacy-safe, decoupled from raw filenames.** Citation labels today are
reverse-engineered from filename stems; filenames can leak content or a person's name (first review,
§3). A visible context pane makes this a prerequisite, not a nicety. **Fix:** render a derived display
label (e.g., *"Week 1 · Session 2 · Slides"*) from facet metadata, never the raw path; partner/guest
material respects the same approval/permission gate as retrieval before it is shown to the cohort or in
any capture.

---

## Important non-blocking concerns

- **Slice already too big (over-bundling).** Both prior reviews warned against bundling; the draft's
  Slice-0 outcome #8 re-bundles. Keep the agentic panel out of Slice 0 (Recommended scope).
- **Gradio reality + "custom HTML is deferred."** The current UI is Gradio with allow-listed trace cards;
  `tech-stack.md:19` defers custom HTML and `AGENTS.md:92-94` forbids web-framework imports in core. A
  polished resizable split-pane pushes Gradio's limits and tempts custom HTML/JS. **Keep the panel in
  Gradio-native components** (a column rendering allow-listed context cards, mirroring the existing
  trace-card pattern, `tech-stack.md:54-56`); defer any custom frontend.
- **Turn-scoped staleness.** The panel must clear/refresh each turn so turn *N*'s answer never sits beside
  turn *N−1*'s evidence (the same per-turn observability-reset concern raised in the provenance work).
- **Multi-lane blending.** Showing several lanes invites cross-lane claim conflation (second review's
  multi-lane-faithfulness finding). Each card carries its own citation; the switcher never implies the
  lanes are equivalent.
- **Cognitive load for the target audience.** A busy "workspace" can overwhelm not-yet-AI-fluent learners.
  Default to a calm single-context view; the switcher is opt-in, collapsed.
- **Agenticity scope creep.** Keep the model's panel "agency" to *ranking among already-cited lanes* and
  *clarify-vs-proceed*, logged in the trace (`AD-7`). It must not gain authority to introduce a new span
  or a new query.

---

## Recommended Slice 0 UI scope

Slice 0 stays the **retrieval/grounding substrate** (notes-exclusion + `corpus_version` + recalibration +
lane-quota selection + per-lane citations + filter-aware refusal + dev eval) and adds **only the panel's
data contract plus an optional minimal, static evidence card**:

1. **Per-turn panel data contract.** Emit, for the current turn: each cited lane's `source_type`,
   `citation_id`, grounding posture (band), a privacy-safe display label (B4), and an extractive excerpt —
   all derived from the existing provenance map. No new retrieval call.
2. **Optional minimal evidence card (read-only).** Render the *primary cited (teaching-role) span* beside
   the answer: label + lane + citation + posture. **No** model-chosen lane featuring, **no** switcher,
   **no** slide images, **no** summaries. This is a projection of `AD-8`/trace-card discipline onto the
   teaching span.
3. **Refusal/clarify states render correctly** (B1/B2): a refused turn shows the refusal/escalation state,
   not a confident card; an ambiguous-in-corpus turn shows the clarifying prompt.
4. Ship through normal gates: builder ≠ reviewer (`/codex`), pytest + ruff + leak check, one real grounded
   trace; frozen `test` split untouched.

If the owner prefers an even leaner Slice 0, ship **only** item 1 (the data contract) and defer the card
to the UI slice — that keeps Slice 0 purely about retrieval correctness.

---

## Deferred UI scope (each its own plan + review + evals)

1. **Tutor Workspace context pane (the agentic panel):** model-chosen lane featuring *among already-cited
   lanes*, the compact source switcher, grounding-posture labels, clarify-vs-proceed in the UI, and the
   two-pane layout. Earns its own eval suite (below).
2. **Slide-image / multimodal rendering:** showing real slide images with grounded alt text — gated as
   multimodal (`roadmap` multimodal pull-in); confirm the asset pipeline first (Open question 1).
3. **Summary cards:** any summarized (non-extractive) context — a second generation behind a grounding
   check.
4. **Cross-session "notes/progress" workspace area, voice narration of context, and web/current-docs in
   the pane:** all later v2 slices already deferred by the PRD.

---

## Right-panel decision policy

Per turn, over the **same** retrieval that grounded the tutor turn:

1. **STOP / no citeable span** → panel shows refusal/escalation state. No evidence card, no clarifying
   "rephrase" fishing. (Out-of-corpus = refuse, `AD-10`.)
2. **Ambiguous but in-corpus** (underspecified, multiple distinct topics, or CONFIRM-band resolvable by a
   narrower query) → panel shows a clarifying prompt; tutor asks one clarifying question; no low-confidence
   card is featured.
3. **CONFIRM / PROCEED with a citeable primary span** → feature the **primary cited (teaching-role)
   span's** lane, chosen by the existing source-priority/provenance selection (slide → handout → first
   citeable), *not* a fresh model choice. If ≥2 lanes were cited this turn, show a compact switcher over
   **only those cited lanes**, defaulting to the primary. Missing lanes are omitted or labeled
   "not found," never shown as empty evidence.
4. **Every card:** privacy-safe label + lane + `citation_id` + grounding posture. Raw scores are not shown
   in committed captures (`AD-12`, trace discipline).
5. **Model's allowed agency:** rank/select which *already-cited* lane to feature, and choose
   clarify-vs-proceed — a choice among grounded options, logged in the trace (`AD-7`). It may **not**
   introduce an uncited span, trigger a second retrieval, or synthesize visual/summary content.

---

## Required metadata / retrieval changes

Mostly already on the v2 roadmap (facet manifest) plus a thin panel contract:

- **Facets at ingest (already planned):** `week`, `session`, `session_type`, `content_kind`(=`source_type`),
  `corpus_version`, optional private `org` — written into chunk metadata.
- **Privacy-safe display label** per source, derived from facets, decoupled from filename (B4). **New.**
- **Per-turn panel payload** per cited span: lane/`source_type`, `citation_id`, `evidence_band`/posture,
  extractive excerpt, display label. Sourced from the existing role-keyed provenance map — **no new query.**
- **Lane-availability summary** for the turn (which lanes returned a citeable span) to drive the switcher
  and the "missing lane labeled" behavior.
- **Posture mapping:** `evidence_band` → a learner-facing label (e.g., "strong / partial match"); keep raw
  scores out of committed artifacts.
- **Deferred:** slide-image asset reference + grounded alt text (multimodal); confirm whether ingestion
  even stores slide images (Open question 1).

---

## Required tests / evals (for the deferred panel slice; data-contract tests in Slice 0)

- **Panel-provenance consistency:** every span rendered in the panel ∈ the turn's provenance map; no panel
  content lacks a `citation_id`.
- **No-invention:** panel payloads are traceable to a retrieved span (panel analog of
  `answer_grounded_in_spans`); no synthesized visual/summary.
- **Refusal coherence:** a refused/STOP turn yields **no** confident context card (B1/B2).
- **Clarify-vs-refuse:** labeled set separating ambiguous-in-corpus (→ clarify) from out-of-corpus
  (→ refuse); assert the floor holds.
- **Lane-label correctness:** displayed lane == span's actual `source_type`; no transcript shown as a
  slide.
- **Switcher faithfulness:** each switcher option maps to a real cited lane; selecting it re-renders an
  already-grounded span (no new retrieval/generation).
- **Turn-scoped freshness:** previous turn's evidence never persists into a new turn.
- All new checks are **scorer-versioned new runs**; v1 golden/scorer/runner and the frozen `test` split
  are untouched.

---

## Accessibility recommendations

- **Reading/DOM order = tutor first.** The answer is primary; the panel follows in DOM order even if it
  sits visually to the side.
- **ARIA live-region discipline.** One primary polite live region (tutor pane); panel updates announced
  politely or on demand, not as competing interruptions — two aggressively-updating regions are a
  screen-reader failure mode.
- **Keyboard path.** Logical tab order reaches the panel and switcher; switcher is operable without a
  mouse.
- **Responsive collapse.** On narrow/mobile widths the pane stacks below or becomes a toggle — never
  horizontal scroll or a lost panel. (A constraint on the Gradio layout choice.)
- **Posture not by color alone.** Grounding posture uses text/icon + color (colorblind-safe).
- **Grounded alt text only.** When slide images land (deferred), alt text comes from corpus/facet
  metadata, never a model-invented description.
- **Calm default** for the not-yet-AI-fluent audience: single context card by default; complexity opt-in.

---

## Privacy / copyright / brand-safety recommendations

- **In-app display to authed cohort learners is fine; captures are not.** Showing corpus content live to
  logged-in learners who have course access is the intended use. **Committed screenshots/demo captures
  must not show raw corpus content** (`AGENTS.md:121-125`; trace discipline) — use redacted/synthetic
  content or keep captures in gitignored `localdocs/`.
- **Filename leakage** → privacy-safe labels (B4).
- **Partner/guest content** respects the same approval/permission gate as retrieval before it appears in
  the pane or any capture (cohort-ops guardrails, second review).
- **Reference screenshots are inspiration only.** Borrow the *generic* pattern — a conversation beside a
  linked source view — which is common across tutoring/docs/IDE tools and is not proprietary to any one
  product. The committed plan should **not name the source product** or imply association.

### What to explicitly avoid copying from the reference screenshots

- Branding, product name, logo, color palette, and typography.
- The exact two-pane proportions, chrome, spacing system, and iconography/button styling.
- Microcopy and labels; their specific onboarding flow and any signature interaction flourish (e.g., a
  distinctive highlight-to-explain mechanic) as a literal reproduction.
- Any visible course/sample content from the screenshots.
- Their information architecture where it is distinctive. Reimplement only the abstract idea (cited claim
  ↔ source span) in GenAcademy's own visual language; originality here is structural (`AGENTS.md:118-120`).

---

## Specific edits recommended for `docs/coach-v2-week1-prd.md`

The PRD already carries an **uncommitted** "### Tutor Workspace UI Direction" subsection, a new Slice-0
outcome #8, and a new acceptance-criterion line. Recommended refinements:

1. **Harden the subsection** to state: (a) **one grounded retrieval per turn; the context pane is a
   projection of the cited spans, not a second query/generation** (B1); (b) clarifying questions are for
   ambiguous-but-in-corpus only — **out-of-corpus = refuse** (B2); (c) **extractive/real-asset only — no
   synthesized visuals or summaries from priors** (B3); (d) **slide-image rendering, summary cards, and
   the source switcher are deferred** to a later UI slice.
2. **Re-scope the new Slice-0 outcome #8.** As drafted ("the tutor workspace can surface the best
   retrieved slide/handout/transcript/Q&A context …") it puts the agentic panel in Slice 0. Replace with
   a **data-contract** outcome: *"Slice 0 emits, per turn, the cited lane(s), privacy-safe labels, and
   grounding posture needed to render a context pane; the agentic workspace pane is a separate, later UI
   slice."* Optionally keep a minimal **read-only** evidence card, explicitly excluding switcher/images/
   summaries.
3. **Add a "Tutor Workspace" risk** under "Technical Risks To Solve First": panel-vs-tutor divergence and
   second-retrieval risk (B1), and the clarify-vs-refuse floor (B2).
4. **Add to "Pre-Build Doc Updates":** a new AD for the companion context pane (below), and a
   privacy-safe-display-label requirement in `corpus/README.md`.
5. **Acceptance criterion:** keep "companion context-pane behavior …" but point it at the **deferred UI
   slice** and the panel-provenance-consistency eval, not Slice 0 build.

*(This review does not apply these edits — per the task it only recommends them; the working-tree PRD
draft remains the owner's WIP.)*

## Specific future edits recommended for specs / ADRs

- **`specs/mission.md`** — add the "learning workspace (tutor + grounded context pane)" framing to v2
  scope; keep the audience-tilt note (calm default, don't overwhelm).
- **`specs/tech-stack.md`** — add a UI note: the context pane is a **provenance projection** rendered in
  **Gradio-native** components under the trace-card allow-list; reaffirm "custom HTML deferred"; add the
  per-turn panel data contract; add pull-in triggers for slide-image/multimodal panel and summary cards.
- **`specs/roadmap.md`** — insert "Tutor Workspace context pane" as a UI slice **after** the Slice-0
  retrieval substrate and **behind** the in-flight #4 false-refusal / #5 recovery work (consistent with
  the PRD sequencing note); phase slide-image/switcher/summaries.
- **`docs/decisions.md`** — add a dedicated AD (next free number after the v2 `AD-14…AD-20` block is
  written, or fold into the lane-selection AD-14): **"Companion Context Pane = Grounded Provenance
  Projection"** — one retrieval per turn; panel renders only cited spans; no second query/generation;
  clarify ≠ refusal bypass; extractive/real-asset only; slide-image/summary/switcher deferred; allow-list
  + privacy-safe labels. (Note: `AGENTS.md:170` still says "AD-1 through AD-12" and is now stale at AD-13 —
  fix opportunistically when the v2 ADs land.)

---

## Open questions for the owner

1. **Slide assets:** does the Week-2 ingestion store slide **images**, or only extracted slide text? This
   decides whether the pane can ever be visual or is text-excerpt-only for the foreseeable slices.
2. **Architectural constraint:** confirm the pane is acceptable as a **read-only projection** of the
   tutor's own retrieval (no independent query/generation). This is the load-bearing assumption of the
   whole review.
3. **Permission scope:** do any Week-1 slides/handouts contain partner/guest or third-party-licensed
   material that cannot be shown to the whole cohort or in any demo capture?
4. **Display labels:** is there an approved privacy-safe label scheme (week/session/lane) to replace raw
   filenames in the pane?
5. **Proof scope:** is the full workspace required to validate v2 on Week 1, or is a single-column tutor +
   minimal evidence card enough to prove the direction (defer the workspace)?
6. **Frontend boundary:** OK to keep the workspace in **Gradio-native** components for now (custom
   HTML/JS deferred)?
7. **"Related material":** should the pane ever show content the tutor did **not** cite? (Recommended:
   **no** for Slice 0 — that is a second answerability decision.)

---

## Direct answers to the 15 review questions (compact)

1. **Product-sound?** Yes, as the v2 vision — with B1/B2/B3 and the scope split.
2. **Strengthen or distract?** Strengthens *if* it renders the tutor's own cited evidence; distracts/risks
   if it's a second retrieval or a busy default. Default calm, opt-in switcher.
3. **What each lane shows?** Slide → real retrieved slide excerpt/asset (image deferred); transcript →
   extracted transcript explanation span; handout → extracted handout excerpt (summary deferred); Q&A →
   approved Q&A excerpt. All extractive, labeled, cited, posture-tagged.
4. **When clarify vs fill?** Clarify on ambiguous-but-in-corpus; refuse on out-of-corpus; fill only with a
   citeable primary span (B2).
5. **Slide vs handout vs transcript vs Q&A?** Reuse existing source priority + role-keyed provenance
   (slide → handout → first citeable); the model only ranks among *already-cited* lanes — no new choice
   of evidence.
6. **Metadata/retrieval needed?** Facets at ingest + privacy-safe label + per-turn panel payload + lane
   availability + posture mapping (see section).
7. **Slice 0 vs deferred?** Slice 0 = substrate + data contract (+ optional static card). Deferred =
   agentic panel, switcher, slide images, summaries.
8. **Hallucination risks?** Panel-tutor divergence; synthesized visuals/summaries; multi-lane blending;
   stale panel; mislabeled lane; clarify-as-refusal-bypass.
9. **Evals?** Panel-provenance consistency, no-invention, refusal coherence, clarify-vs-refuse,
   lane-label, switcher faithfulness, turn freshness — scorer-versioned, v1 untouched.
10. **Accessibility risks?** Dual live regions, keyboard reach, reading order, responsive collapse, color-
    only posture, ungrounded alt text, cognitive overload.
11. **Privacy/copyright risks?** Corpus content in committed captures; filename leakage; partner content
    scope; reproducing the reference UI.
12. **Avoid copying?** Branding, palette, typography, layout proportions, iconography, microcopy,
    signature interactions, their content; borrow only the generic pattern; don't name the product.
13. **PRD edits?** Harden the UI subsection; re-scope outcome #8 to a data contract; add the workspace
    risk; point the acceptance criterion at the deferred slice (section above).
14. **Spec/ADR edits?** mission (workspace framing), tech-stack (provenance-projection + Gradio + deferred
    HTML), roadmap (UI slice after substrate, behind #4/#5), decisions (new context-pane AD).
15. **Ready for the Slice 0 plan?** The **substrate + data contract** is ready to plan; the **agentic
    panel is not** — it is the next, separately-reviewed UI slice. Approve with changes.

---

## Top 3 to do before any code

1. **Adopt the projection constraint (B1)** and the **clarify-vs-refuse floor (B2)** in the PRD, and
   **re-scope Slice-0 outcome #8** to a data contract (move the agentic panel to its own slice).
2. **Write the privacy-safe display-label requirement (B4)** and the extractive/real-asset-only rule
   (B3) as review-blockers.
3. **Write the "Companion Context Pane = Grounded Provenance Projection" AD** and the panel eval list, so
   the panel is review-blockable before anyone builds it.
