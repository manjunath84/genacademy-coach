# Docs Index

This file is the navigation map for new AI sessions and human reviewers. It is not a second
constitution. If anything here conflicts with `AGENTS.md`, `specs/`, or `docs/decisions.md`, those
source-of-truth files win.

## Start Here

Read these before planning or building:

1. `AGENTS.md` - project working agreement, guardrails, review gates, privacy rules.
2. `docs/INDEX.md` - this routing map.
3. `specs/mission.md` - product purpose, audience, in/out of scope.
4. `specs/tech-stack.md` - stack choices, binding implementation guardrails, eval protocol.
5. `specs/roadmap.md` - current priority order and what is deferred.
6. `docs/decisions.md` - settled architecture decisions and rejected alternatives.
7. `docs/build-learnings.md` - non-obvious lessons and the messy reasoning behind changes.

If `localdocs/INDEX.md` exists, read it only for local/private context relevant to the task. Never
commit or quote `localdocs/` content unless the owner explicitly asks.

## Current Priority

For post-Week-4 work, start with:

- `docs/coach-v2-week1-prd.md` - draft PRD/planning record for Coach v2: Week-1 corpus-first rollout,
  default cross-lane synthesis, optional filters, GitHub source acquisition, and staged voice/current-docs
  and cohort-ops roadmap.
- `docs/coach-v2-redesign-second-review.md` - second adversarial review after cohort-ops and Week-1
  corpus direction; identifies lane-starvation as the key Slice-0 retrieval risk.
- `docs/coach-v2-redesign-adversarial-review.md` - first adversarial review of the v2 corpus-filter,
  voice, and current-docs plan.
- `docs/agentic-orchestration-improvement-review.md` - measured diagnosis and orchestration options.
- `docs/post-v1-eval-provenance-learning.md` - beginner-friendly explanation of the merged provenance
  changes and PR #53 review follow-ups.
- `docs/superpowers/plans/2026-06-27-semantic-check-answer-grading.md` - completed plan for
  deterministic concept-aware grading before bounded recovery implementation.
- `docs/superpowers/plans/2026-06-27-bounded-turn2-recovery-orchestration.md` - reviewable plan for the
  bounded Turn-2 recovery slice, with prerequisite gates for false-refusal precision and cheap grading.
- `docs/superpowers/plans/2026-06-26-citation-provenance-audit.md` - completed citation-miss audit plan.
- `docs/superpowers/plans/2026-06-27-role-keyed-provenance.md` - completed role-keyed provenance plus
  deterministic check-span implementation plan.
- `docs/citation-provenance-audit-current-main-r3-20260624.json` - public-safe audit output with
  review buckets, source-family signals, and heuristic citation-F1 ceilings.
- `docs/week4-eval-progress-handoff.md` - detailed eval history, remaining failures, and warnings.
- `docs/week4-eval-dashboard-data.json` - redacted dashboard metrics used for trend evidence.

The current architectural stance is conservative: keep the grounded core, improve false-refusal
precision next, then add one bounded recovery specialist before considering broader multi-agent
orchestration or explicit LangGraph graphs. AD-13 records the future evidence-bound verifier/grader
ladder, but those model-assisted rungs are deferred until eval evidence and egress gates earn them.

## Task Routing

Use this table to avoid opening the whole docs folder blindly.

| Task | Read |
|---|---|
| New feature or architecture change | `AGENTS.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `docs/decisions.md` |
| Teach-loop behavior | `docs/teach-loop-status.md`, `docs/teach-loop-threshold-calibration.md`, `docs/week4-eval-progress-handoff.md` |
| Citation, provenance, or eval failures | `docs/week4-eval-plan.md`, `docs/week4-eval-progress-handoff.md`, `docs/agentic-orchestration-improvement-review.md`, `docs/post-v1-eval-provenance-learning.md`, `docs/superpowers/plans/2026-06-26-citation-provenance-audit.md`, `docs/superpowers/plans/2026-06-27-role-keyed-provenance.md`, `docs/citation-provenance-audit-current-main-r3-20260624.json` |
| Semantic grading, AD-13, or Turn-2 recovery planning | `docs/decisions.md`, `docs/agentic-orchestration-improvement-review.md`, `specs/roadmap.md`, `docs/build-learnings.md`, `docs/post-v1-eval-provenance-learning.md`, `docs/superpowers/plans/2026-06-27-semantic-check-answer-grading.md`, `docs/superpowers/plans/2026-06-27-bounded-turn2-recovery-orchestration.md` |
| Retrieval/index changes | `docs/genacademy-rag-foundation.md`, `docs/foundation-adapter-spec.md`, `docs/teach-loop-retrieval-triage.md`, `specs/tech-stack.md` |
| UI/demo changes | `docs/architecture-diagrams.md`, `docs/teach-loop-status.md`, relevant UI/demo plans in `docs/superpowers/plans/` |
| Deployment | `docs/hugging-face-deployment-plan.md`, `docs/production-roadmap.md` |
| Learning/write-up material | `docs/build-learnings.md`, `docs/agent-concepts-from-genacademy-coach.md`, `docs/agentic-orchestration-improvement-review.md`, `docs/post-v1-eval-provenance-learning.md`, `docs/pr54-bounded-turn2-recovery-learning.md` |

## Source-Of-Truth Hierarchy

Use this order when files disagree:

1. `AGENTS.md` for guardrails and workflow gates.
2. `specs/` for product scope, tech constraints, roadmap, and eval protocol.
3. `docs/decisions.md` for settled architecture decisions.
4. Current approved plan in `docs/superpowers/plans/` for the active implementation slice.
5. Handoffs, status notes, and learnings for context and history.

Historical files are useful evidence, but they do not override the active roadmap or guardrails.

## Key Reference Docs

### Architecture And Decisions

- `docs/decisions.md` - architecture decision records AD-1 through AD-13.
- `docs/architecture.md` - trust boundary and adapter overview.
- `docs/coach-v2-week1-prd.md` - draft PRD/planning record for the Week-1-first Coach v2 direction.
- `docs/coach-v2-redesign-second-review.md` - second-pass adversarial review for Coach v2.
- `docs/coach-v2-redesign-adversarial-review.md` - first-pass adversarial review for Coach v2.
- `docs/architecture-diagrams.md` - Mermaid diagrams for product surface, runtime, state, failure paths,
  eval boundaries, and roadmap.
- `docs/agentic-orchestration-improvement-review.md` - post-feedback orchestration analysis, options,
  and final priority order.
- `docs/superpowers/plans/2026-06-27-semantic-check-answer-grading.md` - implementation plan for the
  completed deterministic semantic grading prerequisite before recovery.
- `docs/superpowers/plans/2026-06-27-bounded-turn2-recovery-orchestration.md` - implementation plan for
  one bounded recovery cycle after a learner stumbles.
- `docs/production-roadmap.md` - longer-term production hardening roadmap.

### Foundation And Retrieval

- `docs/genacademy-rag-foundation.md` - binding reuse contract for the Week-2 RAG foundation.
- `docs/foundation-adapter-spec.md` - adapter surface between Coach and the Week-2 package.
- `docs/teach-loop-retrieval-triage.md` - retrieval diagnosis and likely causes.
- `docs/teach-loop-threshold-calibration.md` - confidence-band evidence and calibration notes.

### Eval And Week-4 Evidence

- `docs/week4-eval-plan.md` - eval design and metric map.
- `docs/week4-eval-progress-handoff.md` - main Week-4 execution handoff.
- `docs/week4-eval-dashboard-data.json` - redacted dashboard data.
- `docs/week4-eval-dashboard.html` - local dashboard artifact.
- `docs/week4-latency-and-failure-fix-plan.md` - latency and failure remediation plan.
- `docs/citation-provenance-audit-current-main-r3-20260624.json` - public-safe citation audit output
  generated from a local current-main golden run.

### Build History And Learning

- `docs/build-learnings.md` - reusable build lessons, newest first.
- `docs/post-v1-eval-provenance-learning.md` - beginner-friendly explanation of the post-v1 eval
  provenance changes, measured result, and PR #53 review follow-ups.
- `docs/pr54-bounded-turn2-recovery-learning.md` - beginner-friendly explanation of the bounded Turn-2
  recovery plan, why it uses one specialist, and why it avoids premature LangGraph/multi-agent scope.
- `docs/teach-loop-status.md` - detailed teach-loop verification history.
- `docs/open-decisions-handoff.md` - resolved early handoff, historical.
- `docs/agent-concepts-from-genacademy-coach.md` - learning notes that explain agent concepts through
  this project.

### Superpowers Plans And Specs

- `docs/superpowers/specs/2026-06-15-genacademy-coach-mvp-design.md` - original MVP design anchor.
- `docs/superpowers/specs/2026-06-23-week4-eval-execution-design.md` - Week-4 eval design.
- `docs/superpowers/specs/2026-06-25-week4-eval-dashboard-design.md` - dashboard design.
- `docs/superpowers/plans/` - implementation plans and review handoffs by date.

## Privacy Notes

Committed docs may contain redacted IDs, aggregate counts, public-safe architecture notes, and safe
trace summaries. They must not contain raw course corpus, raw learner questions, generated tutor prose,
retrieved span text, secrets, private URLs, or frozen `test` split content.

When creating a new doc, prefer:

- public-safe summaries in `docs/`
- active implementation plans in `docs/superpowers/plans/`
- private/local context in ignored `localdocs/`, with `localdocs/INDEX.md` updated
