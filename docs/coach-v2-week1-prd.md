# GenAcademy Coach V2 PRD And Week-1 Corpus Plan

**Date:** 2026-06-29
**Status:** Draft PRD / planning record, pre-implementation
**Source reviews:** `docs/coach-v2-redesign-adversarial-review.md`,
`docs/coach-v2-redesign-second-review.md`

This document captures the GenAcademy Coach v2 direction finalized so far. It is not an implementation
plan yet. Build work still needs an approved implementation plan under `docs/superpowers/plans/`, with
tests, leak checks, and a separate reviewer gate.

## Product Goal

Turn GenAcademy Coach from the Week-3/Week-4 grounded tutor into a course-learning assistant that can
answer questions, tutor concepts, quiz learners, and later support voice, current-docs checks, cohort
operations, and admin workflows without weakening the core rule: course claims must be grounded in
retrieved evidence or refused.

The near-term product goal is narrower: prove v2 on **Week 1 only**, using the first week's approved
course materials before expanding to later weeks.

## Finalized Direction

### Week-1 Corpus First

Slice 0 starts with the Week-1 corpus only:

- two live-session transcripts;
- handouts;
- slides/PPTs if available;
- curated course Q&A or handout Q&A if available;
- no video dependency for now.

Live transcripts are the canonical source for instructor explanations until video files are available.
If video is added later, it can enrich timestamps, audio references, or voice features, but it does not
block v2 Slice 0.

### Source Acquisition

Course materials may live behind GitHub URLs provided by the project owner.

The system and implementation process must follow this rule:

- If a required GitHub URL or source path is provided, use only that owner-provided source.
- If a required GitHub URL or source path is missing, stop and ask the owner for it.
- Do not guess, search broadly, or pull private course material from unrelated locations.
- Treat owner-provided GitHub course material as private course corpus, not as public external web
  evidence.

This is separate from current-docs/web verification. GitHub course URLs populate the course corpus.
Context7/Tavily-style lookups are only for current external documentation or web evidence when enabled
for eligible course-related topics.

### Default Answer Behavior

By default, learners should not have to choose filters. The default is "all approved Week-1 corpus
selected."

When a learner asks a Q&A or tutor question, the answer should synthesize across available evidence
lanes when the corpus supports them:

- slide/PPT framing;
- live transcript explanation;
- handout or cohort Q&A;
- relevant guest/partner-session material, when present.

Missing lanes must be omitted or explicitly labeled as not found. The system must never invent a slide,
transcript, Q&A, or guest-session source.

### Optional Filters

Filters are optional narrowing controls, not required setup.

Initial filter dimensions:

- resource type: slides, transcripts, handouts/Q&A;
- week: Week 1 in the first slice;
- session: Session 1 or Session 2, when metadata is available.

Future filter dimensions:

- guest/session type;
- private organization/speaker metadata;
- topic tags;
- corpus version.

If a learner narrows the filter and no citeable evidence remains, the app should give a filter-aware
refusal and suggest broadening scope. It must not silently widen the filter.

### Teaching Lenses

Keep the existing learner-facing teaching lenses:

- low-code/no-code;
- code-heavy AI;
- combined/bridge.

For v2, teaching lens is prompt-level explanation personalization only. It should not restrict retrieval
unless a later eval proves track-aware retrieval improves correctness without harming faithfulness.

Future onboarding questions such as learner role or industry can personalize examples and practice
framing later, but should not change facts, citations, or retrieval scope.

### Tutor Workspace UI Direction

The v2 tutor experience should feel like a learning workspace, not only a chat box. Use the external
AI-tutor screenshots discussed during planning as directional reference only; do not copy their layout,
branding, typography, or visual assets.

The useful pattern to borrow is:

- a conversational tutor pane that explains, checks understanding, and asks clarifying questions when the
  learner's request is ambiguous;
- a companion context pane that shows the most relevant grounded course artifact for the current turn;
- a lightweight progress or notes area that helps the learner orient themselves without overwhelming the
  tutor flow.

For GenAcademy Coach, the companion context pane must be a projection of the same grounded retrieval and
role-keyed provenance that produced the tutor response. It must not run a second query, introduce a new
span, or generate a second answerability decision that can disagree with the tutor pane.

The agent's allowed UI decision is narrow: choose how to render already-cited evidence, or ask a
clarifying question when the question is ambiguous but still appears to be in-corpus. Below STOP or with
no citeable span, the tutor refuses and escalates; it does not ask for a rephrase to bypass the refusal
floor.

For the later full workspace slice, the companion pane can render already-cited evidence like this:

- if a matching slide exists, show the relevant slide or slide-derived visual context;
- if the handout is the stronger evidence, show the relevant handout excerpt or summary card;
- if the live transcript contains the clearest explanation, show the transcript-backed explanation lane;
- if multiple lanes are useful, show a compact source switcher rather than crowding the screen;
- if the topic is ambiguous but in-corpus, ask a clarifying question before filling the context pane with
  low-confidence material.

This right-side pane must remain evidence-bound. It should not become decorative content generated from
model priors. The panel title, source label, citation, and lane should make clear whether the visible
context came from slides, handouts, transcripts, or approved Q&A. In Slice 0, this means the system emits
the per-turn context-pane data contract and may render only a minimal read-only evidence card. Slide
images, source switchers, summary cards, and richer two-pane workspace behavior are deferred to a
separately reviewed UI slice. Any later summary card must pass the same grounding checks as the tutor
answer; otherwise the pane should show an extractive span, not a generated summary.

### Frontend Boundary

Keep the next Coach v2 slices Gradio-native. Slice 0 and the first minimal evidence-card UI should prove
the corpus, retrieval, citation, refusal, and context-pane data contract without a frontend migration.
Do not introduce FastAPI, HTMX, or custom HTML as part of Slice 0.

FastAPI + HTMX remains the preferred production web edge, but only after the application service
boundary is in place. The sequence is:

1. define UI-neutral service methods and typed DTOs for Teach, Quiz, Skill-Gap, auth/admin, review queue,
   memory status, and the context-pane payload;
2. make the existing Gradio surface call those services;
3. add FastAPI + HTMX under the web edge when the product needs stronger route-level tests, session
   resume, progress/SSE behavior, admin flows, and production accessibility control.

The core rule does not change: retrieval, grading, tutor decisions, learner profile, traces, and corpus
selection stay framework-free. Gradio and any future FastAPI/HTMX surface are thin views over the same
services.

## Slice 0 Scope

Slice 0 is learner retrieval only: no admin UI, no voice, no current-docs/web, no admin upload.

Required outcomes:

1. Week-1 corpus manifest exists and validates every approved source file.
2. Notes are excluded from learner retrieval.
3. Each indexed chunk has metadata such as `week`, `session`, `session_type`, `content_kind`,
   `corpus_version`, and optional private organization/speaker fields.
4. Default retrieval over-fetches and uses source-lane balancing so transcript/handout/Q&A evidence is
   not starved by slide priority.
5. Optional filters are strict when active.
6. Answers show per-lane citations.
7. Missing lanes are omitted or labeled as not found.
8. Slice 0 emits, per turn, the cited lane(s), citation IDs, privacy-safe display labels, extractive
   excerpts, and grounding posture needed to render a future context pane.
9. Optionally, Slice 0 may render a minimal read-only evidence card for the primary cited teaching span;
   it must not include a source switcher, slide images, generated summaries, or an independent panel
   retrieval.
10. Confidence bands are recalibrated for the new Week-1 corpus version.
11. Dev eval is rerun and recorded as a new corpus-version result.
12. Frozen held-out eval data remains untouched and unindexed.

## Technical Risks To Solve First

### Lane Starvation

The second review identified the main retrieval risk: current selection likely reorders by source
priority and truncates, which can starve transcripts or handouts. Slice 0 must solve this with
over-fetch plus lane-aware selection.

### Notes Exclusion

Removing notes changes answerability and thresholds. It requires a fresh `corpus_version`,
recalibration, and dev eval run.

### Multi-Lane Faithfulness

Synthesizing across slides, transcripts, and handouts increases the risk of blending claims. Every shown
lane needs its own citations and tests that verify claims resolve to the correct lane.

### Panel-Tutor Divergence

The companion context pane can undermine grounding if it runs a second retrieval, shows content the tutor
did not cite, or generates a visual/summary from model priors. The panel must render only spans already
present in the current turn's provenance map. Clarifying questions are allowed only for
ambiguous-but-in-corpus cases; out-of-corpus or below-STOP questions must still refuse and escalate.

### Filter Leakage (Top-Span Injection)

When an optional filter is active, selection must not re-admit a non-matching span. Current selection
force-injects the single highest-scored span even when it fails the active facet filter, so a narrowed
("slides-only", "Week-1-only") answer can still surface an off-lane or off-week chunk. The top-span
injection must become filter-aware, with a test asserting that no returned or cited span carries a
non-matching facet. See `docs/coach-v2-redesign-adversarial-review.md` (B1).

## Later Roadmap

> **Sequencing.** This Slice 0–6 order is the *internal* v2 sequence. It sits **after** the in-flight
> roadmap work that `specs/roadmap.md` still marks as binding-next — CONFIRM-band false-refusal
> precision (#4) and bounded Turn-2 recovery (#5). v2 is not scheduled ahead of that work unless the
> owner explicitly reprioritizes, in which case `specs/roadmap.md` must record the change. Both
> adversarial reviews flag this; the two roadmaps must not disagree about what is next.

1. **Slice 0 - Week-1 learner retrieval:** notes excluded, manifest metadata, cross-lane synthesis,
   optional filters, recalibration, dev eval.
2. **Slice 1 - Read-only corpus inventory:** admin-visible source inventory and chunk/stat counts, no
   mutation.
3. **Slice 2 - Cohort access management:** invite codes and account lifecycle, reusing Week-2 security
   primitives where appropriate.
4. **Slice 3 - Current-docs/web verification:** null provider and answer contract first, then official
   docs/Context7-style lookup, then Tavily-style broader web, then default-on for a narrow eligible set.
5. **Slice 4 - Voice:** push-to-talk and optional play-audio over grounded text; standard licensed voice
   first; tutor voice clone only after explicit written consent and retention controls.
6. **Slice 5 - Admin upload:** late, gated, corpus-versioned, pending-review, leak-checked,
   recalibrated, rollback-able.
7. **Slice 6 - Cohort analytics:** aggregate/hashed only; no raw questions, raw speech transcripts, or
   direct identifiers by default.

## Current-Docs/Web Policy

Current-docs/web verification is for course-related topics that may have changed since the course was
recorded, such as SDKs, APIs, cloud setup, security practices, observability, MCP development, and
fast-moving AI tooling.

Target behavior:

- default-on only after adapters, egress minimization, provenance separation, and eval gates exist;
- learner can disable it for course-only answers;
- official docs lookup before broader Tavily-style web retrieval;
- separate course citations from external citations;
- if course-era and current guidance conflict, label both clearly;
- external evidence never enters the course index or corpus version.

## Voice Policy

Text remains canonical. Audio is generated only after the answer passes retrieval, citation, and
grounding/refusal gates.

First voice slice should be:

- push-to-talk or microphone input;
- speech transcript feeds the existing grounded tutor/Q&A path;
- text answer appears first;
- learner can optionally play the answer as audio.

Tutor voice cloning is not allowed without explicit written, revocable consent from the tutor for this
specific use, approved sample provenance, in-app disclosure, retention/deletion controls, and scope
limited to this app's narration.

## Cohort Operations Policy

Reuse the Week-2 RAG project's hard-won safety ideas, but do not copy its admin UI directly.

Reuse or preserve conceptually:

- bcrypt auth and admin/member roles;
- invite-code scheme: `id.secret`, secret hashed at rest, role-bound, single-use, expiring, revocable;
- content-hash upload storage when uploads are eventually added;
- uploaded-by provenance;
- protected eval/curriculum collections;
- corpus mutation locks;
- no filename trust for uploads.

Redesign:

- admin UI for Coach's Gradio/product surface;
- analytics so dashboards use aggregate/hashed data, not raw learner questions or email addresses.

Defer:

- admin upload;
- delete/reindex;
- cohort analytics with raw question visibility;
- production-grade auth changes.

## Privacy And Guardrails

The following must be review-blockers before implementation:

- Default Q&A selects all approved lanes and synthesizes only evidence-backed lanes.
- Optional filters are strict; filtered-empty means refusal, not silent widening.
- Any corpus mutation bumps `corpus_version` and requires leak check, recalibration, and dev eval before
  learner visibility.
- Eval, curriculum, and held-out splits are immutable to admin actions.
- Uploads are untrusted input and require content-hash storage, type/size validation, and permission
  confirmation before learner visibility.
- Cohort analytics are aggregate/hashed by default.
- Invite codes are never committed or logged in plaintext.
- Voice samples, learner audio, generated audio, private transcripts, private source URLs, and raw
  screenshots must not be committed.

## Open Inputs Needed From Owner

Before Slice 0 implementation, the owner needs to provide:

- Week-1 GitHub URL(s) or local paths for Session 1 transcript.
- Week-1 GitHub URL(s) or local paths for Session 2 transcript.
- Week-1 GitHub URL(s) or local paths for handouts.
- Week-1 GitHub URL(s) or local paths for slides/PPTs, if available.
- Week-1 GitHub URL(s) or local paths for curated Q&A, if available.
- Confirmation of which Week-1 files are approved for learner retrieval.
- Confirmation that notes should remain excluded.

If any of these inputs are missing during planning or implementation, the agent must ask the owner.

## Pre-Build Doc Updates

Before code, update or create the following:

- `AGENTS.md`: add v2 source-lane, corpus-versioning, source-acquisition, and cohort-ops guardrails.
- `specs/mission.md`: describe Week-1 corpus-first cross-lane learning.
- `specs/tech-stack.md`: document manifest metadata, `corpus_version`, lane-aware retrieval, and source
  acquisition.
- `specs/roadmap.md`: add Slice 0 through Slice 6 sequence.
- `docs/decisions.md`: add ADs for source-lane synthesis, current-docs/web, voice, voice cloning,
  guest/private metadata, cohort ops, corpus-versioning, and the companion context pane as a grounded
  provenance projection.
- `docs/foundation-adapter-spec.md`: describe the retriever/filter/lane-selection delta.
- `corpus/README.md`: document approved source layout, private GitHub URL handling, manifest rules, and
  privacy-safe display labels that decouple UI labels from raw filenames.

## Acceptance Criteria For Slice 0 Plan

An implementation plan for Slice 0 is ready only when it includes:

- exact Week-1 source list or placeholders that require owner input;
- manifest schema and validation tests;
- retrieval filter and source-lane selection design;
- refusal behavior for filtered-empty cases;
- per-lane citation behavior;
- per-turn companion context-pane data contract for already-cited slide/handout/transcript/Q&A evidence;
- panel-provenance consistency tests, with the full agentic context pane deferred to a separate UI slice;
- eval/leak/recalibration commands;
- privacy checks for source URLs and corpus material;
- a separate reviewer step before build.
