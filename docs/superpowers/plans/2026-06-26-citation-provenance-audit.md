# Citation Provenance Audit And Roadmap Reprioritization Plan

> **For agentic workers:** This is a planning artifact only. Do not implement code from this file until
> the plan is reviewed and approved. Use the repo gates in `AGENTS.md`: builder and reviewer must be
> different contexts, evidence is required before "done", and the frozen `test` split remains untouched.

**Goal:** Establish the next implementation slice after Week-4 evaluation: audit citation misses,
design role-keyed provenance, and update the roadmap so future orchestration work follows measured
failure modes instead of adding agents for architecture optics.

**Architecture:** Keep the current LangChain `create_agent` teach loop. Add no direct `langgraph.*`
imports in this slice. Treat provenance and check-span selection as deterministic product behavior.
Turn-2 recovery, memory-personalized recovery, mock interview, and explicit LangGraph remain future
plans until this slice has evidence.

**Tech Stack:** Python 3.12, existing local golden eval artifacts, existing redacted eval runners,
Markdown docs, existing leak/privacy checks.

---

## Scope

### In Scope

- Audit citation misses on seed/dev/golden rows already approved for local evaluation.
- Categorize citation misses without exposing private learner text or retrieved span text in committed
  artifacts.
- Define a role-keyed provenance model, for example `role -> span_id`, where roles may include
  `teaching`, `check`, `recovery`, and `final`.
- Define deterministic check-span selection policy.
- Define how citation F1 is reported when labels are audited or changed.
- Update the repo roadmap to reflect the reviewed priority order.

### Out Of Scope

- Product code changes.
- New eval dataset rows.
- Direct `langgraph.*` imports.
- Turn-2 recovery implementation.
- Confirm-band false-refusal implementation.
- Semantic grading implementation.
- Mock interview.
- Memory hardening.
- Any use of the frozen `test` split.

---

## Success Criteria

- [ ] A citation-miss taxonomy is defined: real miss, acceptable sibling span, label error, ambiguous
      source-family match.
- [ ] A public-safe audit output format is defined that does not include raw learner text, raw tutor
      prose, raw retrieved spans, private URLs, secrets, or frozen test data.
- [ ] The plan states how to avoid moving the goalposts: if labels change, freeze a labeled-v2 golden
      set and re-run the baseline against it before reporting product deltas.
- [ ] Role-keyed provenance is specified as a general record shape instead of hardcoded one-off fields.
- [ ] Deterministic check-span selection is specified: prefer slide, then handout, then first citeable
      span unless the audit proves a better policy.
- [ ] Roadmap order is updated so citation/provenance and false-refusal precision precede Turn-2
      recovery.
- [ ] No implementation code is changed by this planning slice.

---

## Planned File Changes

- Create or update this plan:
  - `docs/superpowers/plans/2026-06-26-citation-provenance-audit.md`
- Update the roadmap:
  - `specs/roadmap.md`
- Already-created learning record to reference:
  - `docs/agentic-orchestration-improvement-review.md`

No source files should be changed by this plan.

---

## Proposed Audit Model

### Citation Miss Taxonomy

| Category | Meaning | Product implication |
|---|---|---|
| Real miss | The predicted citation does not support the expected concept. | Product behavior needs improvement. |
| Acceptable sibling span | The predicted citation is from the same source family and supports the answer, but differs from the label. | Labeling or scoring may need role/source-family awareness. |
| Label error | The expected citation is wrong, stale, or too narrow. | Create labeled-v2 and re-run baseline. |
| Ambiguous source-family match | Multiple retrieved chunks reasonably support the same concept. | Scoring should report exact-match and family-level views separately. |

### Public-Safe Audit Row

Committed audit rows, if any, should use only redacted identifiers and aggregate labels:

```json
{
  "case_id": "happy_014",
  "run_id": "current-main-r2",
  "citation_miss_category": "acceptable_sibling_span",
  "expected_source_type": "slide",
  "predicted_source_type": "handout",
  "expected_role": "teaching",
  "predicted_role": "check",
  "notes": "source-family match; no raw text stored"
}
```

Do not commit raw question text, tutor prose, retrieved span text, raw trace JSON, private LangSmith
URLs, or frozen `test` data.

---

## Role-Keyed Provenance Design

Prefer one general provenance record keyed by role:

```json
{
  "role": "check",
  "span_id": "slide/week2-session1-example::3",
  "source_type": "slide",
  "selected_at": "check_generation",
  "selection_reason": "first_slide_citeable"
}
```

Why this shape:

- It generalizes to Teach, Quiz, Skill-Gap, and future Mock Interview.
- It avoids adding new schema fields every time a new mode needs a citation role.
- It keeps the invariant simple: provenance is captured when evidence is selected, never reconstructed
  after generation.
- It allows `final` to reference an existing `teaching` or `recovery` span rather than pretending every
  output has a separate retrieval event.

Initial roles:

| Role | Producer | Notes |
|---|---|---|
| `teaching` | Retrieval/span-selection before explanation | Current teach explanation evidence. |
| `check` | Check-item generation | Prefer slide, then handout, then first citeable span. |
| `final` | Session/result boundary | May reference `teaching` or `check`; do not force a new span. |
| `recovery` | Future Turn-2 recovery loop | Deferred until recovery implementation plan. |

---

## Deterministic Check-Span Policy

Initial policy:

1. First retrieved citeable `slide`.
2. First retrieved citeable `handout`.
3. First retrieved citeable span.
4. No span means refuse/escalate; do not synthesize a citation.

Open question for implementation planning:

- Should exact source type priority always beat higher similarity score, or should the policy use a
  score floor such as "prefer slide only if its score is within X of the top citeable span"? This should
  be decided from the audit, not guessed.

---

## Reporting Rules

Keep these deltas separate:

| Delta type | What it means | How to report |
|---|---|---|
| Label audit delta | F1 changes because labels or acceptable-span criteria changed. | Report separately as relabeling/scoring movement. |
| Product delta | F1 changes because product behavior selected better provenance. | Report baseline vs new run on the same frozen labels. |
| Scorer-version delta | F1 changes because the metric definition changed. | Version the scorer and re-run baseline under the new scorer. |

If a labeled-v2 golden set is created, re-run the current baseline on labeled-v2 before comparing any
new product behavior. Do not compare old-label baseline to new-label product runs.

---

## Implementation Plan After Approval

### Implementation Progress - 2026-06-26

- Added `scripts/audit_citation_provenance.py`, a public-safe audit CLI that reads a redacted golden
  run artifact and emits review buckets, source-family/type signals, counts, and heuristic ceilings.
- Added focused tests in `tests/test_audit_citation_provenance.py`.
- Generated `docs/citation-provenance-audit-current-main-r3-20260624.json` from the local
  `current-main-full-langsmith-r3` run. The source run remains local/ignored; the committed audit output
  contains only IDs, aggregate labels, buckets, counts, and scores.
- The automated audit intentionally leaves `citation_miss_category` as `null`; final taxonomy labels
  still require human/source review before any relabeling or product comparison.

### Task 1: Prepare Audit Inputs

- [x] Identify the current golden run artifacts that can be inspected locally.
- [x] Confirm no frozen `test` split files are used.
- [x] Confirm audit output can be generated with case IDs, citation IDs/source types, roles, and scores
      only.

### Task 2: Produce Citation-Miss Taxonomy

- [ ] Classify each citation miss using the taxonomy above.
- [x] Count misses by automated review bucket, expected source type, and scenario type.
- [x] Estimate heuristic reachable citation-F1 ceiling after removing exact-extra and same-source-family
      ambiguity.

### Task 3: Decide Label Handling

- [ ] If labels are unchanged, record the audit as context only.
- [ ] If labels need changes, create a labeled-v2 proposal and re-run the baseline against it before
      any product changes.

### Task 4: Design Provenance Objects

- [ ] Add a small design note or update this plan with final provenance fields.
- [ ] Specify how provenance appears in traces/eval rows without leaking private text.
- [ ] Specify per-role citation F1 reporting.

### Task 5: Plan Product Implementation

- [ ] Create a separate implementation plan for role-keyed provenance and deterministic check-span
      policy.
- [ ] Include focused unit tests and golden-eval commands in that plan.
- [ ] Require a fresh reviewer before build.

---

## Verification Commands For The Planning Slice

Docs-only checks:

```bash
rg -n "raw learner|raw tutor|retrieved span text|smith.langchain.com|week3-session1" \
  docs/superpowers/plans/2026-06-26-citation-provenance-audit.md specs/roadmap.md
```

Before any later implementation PR:

```bash
uv run ruff check .
uv run pytest -q
uv run python scripts/check_eval_leak.py
uv run python scripts/check_memory_leak.py
```

Provider-backed eval remains local/credential-gated and must not touch the frozen `test` split.

---

## Risks

| Risk | Mitigation |
|---|---|
| Relabeling looks like product improvement | Separate label delta from product delta and re-run baseline on labeled-v2. |
| Audit leaks private content | Commit only IDs, categories, source types, scores, and aggregate counts. |
| Check-span policy overfits to current labels | Validate by source-family and scenario type, not one case. |
| Roadmap turns into implementation without review | Keep this as a plan; require approval before code. |
| Turn-2 recovery starts too early | Explicitly gate recovery behind provenance, false-refusal, and cheap semantic grading work. |

---

## Deferred Follow-Up Plans

Create these only after this plan is reviewed:

1. `docs/superpowers/plans/2026-06-26-role-keyed-provenance.md`
2. `docs/superpowers/plans/2026-06-26-confirm-band-false-refusal.md`
3. `docs/superpowers/plans/2026-06-26-synonym-concept-grading.md`
4. `docs/superpowers/plans/2026-06-26-turn-2-recovery-loop.md`

Each follow-up plan gets its own review gate and evidence bar.
